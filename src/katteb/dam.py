"""TravelMediaDAM resolver, two-phase ImageMagick + ExifTool optimizer, and semantic HTML figure injector."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import logging
import os
import re
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger("katteb.dam")

DEFAULT_DAM_PLACES_CSV = Path(
    os.environ.get("KATTEB_DAM_PLACES_CSV", "/Volumes/External-HD/TravelMediaDAM/locations/places.csv")
)
DEFAULT_DAM_ORIGINALS_DIR = Path(
    os.environ.get("KATTEB_DAM_ORIGINALS_DIR", "/Volumes/WD-Passport/01_LIBRARY/photos/originals")
)

AI_TROPE_WORDS = [
    "nestled",
    "tapestry",
    "beacon of serenity",
    "testament to",
    "sun-drenched",
    "picturesque",
]

DONKEY_BAN_PATTERNS = [
    r"\bdonkey\s+ride",
    r"\briding\s+(?:a\s+)?donkey",
    r"\bride\s+(?:a\s+|the\s+)?donkey",
    r"\bdonkey\s+taxi",
    r"\bdonkeys?\s+carrying\s+luggage",
    r"\bdonkey\s+luggage",
    r"\bdonkey[_\s-]*transit",
    r"\bsantorini[_\s-]*donkey",
    r"\bfira[_\s-]*donkey",
    r"\beselreiten\b",
]


class DAMMediaItem(BaseModel):
    """Represents a curated authentic travel photo from TravelMediaDAM."""

    model_config = ConfigDict(extra="allow")

    asset_id: str
    file_path: str
    city: str = ""
    region: str = ""
    country: str = ""
    title: str = ""
    caption: str = ""
    alt_text: str = ""
    keywords: list[str] = []
    sha256: str = ""
    public_url: str = ""
    width: int | None = None
    height: int | None = None
    bytes_size: int | None = None


def sanitize_editorial_title(title: str) -> str:
    """Clean photo title per IPTC cleanliness rules: strip copyright/creator attribution and trailing punctuation."""
    if not title:
        return ""
    cleaned = re.sub(r"©\s*Kyle\s+Kroeger", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:Photo\s+by|By)\s+Kyle\s+Kroeger\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bKyle\s+Kroeger\b", "", cleaned, flags=re.IGNORECASE)
    for trope in AI_TROPE_WORDS:
        cleaned = re.sub(rf"\b{re.escape(trope)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(".,;:!|-–— ")
    return cleaned


def sanitize_editorial_caption(caption: str) -> str:
    """Clean visible photo caption per IPTC cleanliness rules: purge copyright/creator notices and AI tropes."""
    if not caption:
        return ""
    cleaned = re.sub(r"©\s*Kyle\s+Kroeger\.?", "", caption, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:Photo\s+by|Credit:|By)\s*Kyle\s+Kroeger\.?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bKyle\s+Kroeger\b", "", cleaned, flags=re.IGNORECASE)
    for trope in AI_TROPE_WORDS:
        cleaned = re.sub(rf"\b{re.escape(trope)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned


def is_prohibited_donkey_media(item_or_text: DAMMediaItem | dict[str, Any] | str, country: str = "") -> bool:
    """Return True if an asset or text depicts prohibited donkey riding or luggage transit in Greece."""
    if isinstance(item_or_text, DAMMediaItem):
        haystack = " ".join(
            [
                item_or_text.file_path,
                item_or_text.title,
                item_or_text.caption,
                item_or_text.alt_text,
                item_or_text.city,
                item_or_text.region,
                item_or_text.country,
                " ".join(item_or_text.keywords),
            ]
        ).lower()
        effective_country = (country or item_or_text.country or "").lower()
    elif isinstance(item_or_text, dict):
        haystack = " ".join(str(v) for v in item_or_text.values() if v is not None).lower()
        effective_country = (country or str(item_or_text.get("country", ""))).lower()
    else:
        haystack = str(item_or_text).lower()
        effective_country = (country or "").lower()

    is_greek = effective_country in ("gr", "greece", "el", "hellas") or any(
        tok in haystack for tok in ("santorini", "greece", "fira", "oia", "cyclades", "mykonos", "hydra", "rhodes")
    )
    if not is_greek:
        return False

    for pat in DONKEY_BAN_PATTERNS:
        if re.search(pat, haystack, re.IGNORECASE):
            return True

    if "donkey" in haystack or "mule" in haystack:
        return True

    return False


def compute_file_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 hex digest of a local file if it exists, otherwise hash its normalized path string."""
    p = Path(file_path)
    if p.is_file():
        digest = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()


def optimize_media_asset(
    src_path: str | Path,
    output_dir: str | Path,
    title: str = "",
    caption: str = "",
    city: str = "",
    country: str = "",
    creator: str = "Kyle Kroeger",
    copyright_notice: str = "© Kyle Kroeger",
    max_bytes: int = 1_000_000,
) -> dict[str, Any]:
    """Execute the mandatory two-phase ImageMagick + ExifTool web optimization sequence."""
    src = Path(src_path)
    if not src.is_file():
        raise FileNotFoundError(f"Source media asset not found at '{src}'.")

    if is_prohibited_donkey_media(f"{src.name} {title} {caption} {city}", country=country):
        raise ValueError("Cultural & ethical policy violation: Cannot optimize or stage Greece donkey transit media.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{src.stem}.jpg"

    clean_title = sanitize_editorial_title(title or src.stem.replace("-", " ").replace("_", " ").title())
    clean_caption = sanitize_editorial_caption(caption or clean_title)

    # Phase 1: ImageMagick resize, 4:2:0 chroma subsampling, strip raw bloat, progressive JPEG quality 82
    magick_cmd = [
        "magick",
        str(src),
        "-auto-orient",
        "-resize",
        "2048x2048>",
        "-sampling-factor",
        "4:2:0",
        "-strip",
        "-quality",
        "82",
        "-interlace",
        "Plane",
        str(dst),
    ]
    magick_res = subprocess.run(  # nosec B603
        magick_cmd,
        shell=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if magick_res.returncode != 0:
        raise RuntimeError(f"ImageMagick optimization failed for '{src}': {magick_res.stderr or magick_res.stdout}")

    # Phase 2: ExifTool IPTC legal attribution & location metadata injection (never strip after tagging)
    exif_cmd = [
        "exiftool",
        "-overwrite_original",
        f"-Creator={creator}",
        f"-Artist={creator}",
        f"-By-line={creator}",
        f"-CopyrightNotice={copyright_notice}",
        f"-Copyright={copyright_notice}",
        f"-ObjectName={clean_title}",
        f"-Title={clean_title}",
        f"-Caption-Abstract={clean_caption}",
        f"-ImageDescription={clean_caption}",
    ]
    if city:
        exif_cmd.append(f"-City={city}")
    if country:
        exif_cmd.append(f"-Country={country}")
    exif_cmd.append(str(dst))

    exif_res = subprocess.run(  # nosec B603
        exif_cmd,
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if exif_res.returncode != 0:
        raise RuntimeError(f"ExifTool IPTC injection failed for '{dst}': {exif_res.stderr or exif_res.stdout}")

    final_size = dst.stat().st_size if dst.is_file() else 0
    if final_size > max_bytes:
        raise ValueError(
            f"Optimized image '{dst}' size ({final_size} bytes) exceeds maximum allowed limit ({max_bytes} bytes)."
        )

    return {
        "success": True,
        "source_path": str(src),
        "output_path": str(dst),
        "bytes_size": final_size,
        "sha256": compute_file_sha256(dst),
        "title": clean_title,
        "caption": clean_caption,
        "creator": creator,
        "copyright": copyright_notice,
    }


def inject_dam_media_into_html(
    html_content: str,
    media_items: list[DAMMediaItem],
    max_images: int = 3,
) -> str:
    """Inject semantic WordPress <figure> blocks after H2 sections using sanitized captions and alt text."""
    if not html_content or not media_items or max_images <= 0:
        return html_content

    selected = [item for item in media_items if not is_prohibited_donkey_media(item)][:max_images]
    if not selected:
        return html_content

    soup = BeautifulSoup(html_content, "html.parser")
    h2_tags = soup.find_all("h2")
    if not h2_tags:
        return html_content

    existing_srcs = {
        str(img.get("src", "")).strip() for img in soup.find_all("img") if img.get("src")
    }

    injected_count = 0
    for idx, item in enumerate(selected):
        if idx >= len(h2_tags):
            break
        img_src = (item.public_url or item.file_path or "").strip()
        if not img_src or img_src in existing_srcs:
            continue

        clean_title = sanitize_editorial_title(item.title or item.city or "Travel Guide Photo")
        clean_caption = sanitize_editorial_caption(item.caption or clean_title)
        clean_alt = sanitize_editorial_caption(item.alt_text or clean_caption or clean_title)

        figure_html = (
            '<figure class="wp-block-image size-large katteb-dam-media">'
            f'<img src="{html.escape(img_src, quote=True)}" '
            f'alt="{html.escape(clean_alt, quote=True)}" '
            f'title="{html.escape(clean_title, quote=True)}" loading="lazy"/>'
            f"<figcaption>{html.escape(clean_caption)}</figcaption>"
            "</figure>"
        )
        figure_fragment = BeautifulSoup(figure_html, "html.parser")

        target_h2 = h2_tags[idx]
        next_p = target_h2.find_next_sibling("p")
        if next_p is not None:
            next_p.insert_after(figure_fragment)
        else:
            target_h2.insert_after(figure_fragment)

        existing_srcs.add(img_src)
        injected_count += 1

    if injected_count == 0:
        return html_content
    return str(soup)


class TravelMediaDAMResolver:
    """Resolves authentic fleet photography from TravelMediaDAM CSV/JSON manifests with deduplication."""

    def __init__(
        self,
        catalog_path: str | Path | None = None,
        originals_dir: str | Path | None = None,
    ):
        self.catalog_path = Path(catalog_path) if catalog_path else DEFAULT_DAM_PLACES_CSV
        self.originals_dir = Path(originals_dir) if originals_dir else DEFAULT_DAM_ORIGINALS_DIR

    def is_available(self) -> bool:
        """Return True if the catalog manifest or originals directory is mounted and accessible."""
        return self.catalog_path.is_file() or self.originals_dir.is_dir()

    def load_catalog(self) -> list[DAMMediaItem]:
        """Load DAMMediaItem entries from CSV or JSON catalog manifest, returning [] if offline."""
        if not self.catalog_path.is_file():
            logger.info("TravelMediaDAM catalog not mounted at '%s'; returning empty catalog.", self.catalog_path)
            return []

        items: list[DAMMediaItem] = []
        suffix = self.catalog_path.suffix.lower()
        try:
            if suffix == ".json":
                raw_data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
                rows = raw_data if isinstance(raw_data, list) else raw_data.get("items", [])
            else:
                with open(self.catalog_path, encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                file_path = str(
                    row.get("file_path")
                    or row.get("path")
                    or row.get("filepath")
                    or row.get("filename")
                    or ""
                ).strip()
                if not file_path:
                    continue

                raw_kw = row.get("keywords") or row.get("tags") or ""
                if isinstance(raw_kw, list):
                    kw_list = [str(k).strip() for k in raw_kw if str(k).strip()]
                else:
                    kw_list = [k.strip() for k in re.split(r"[,;]", str(raw_kw)) if k.strip()]

                raw_sha = str(row.get("sha256") or row.get("checksum") or "").strip()
                sha_val = raw_sha if raw_sha else compute_file_sha256(file_path)

                title_val = sanitize_editorial_title(str(row.get("title") or row.get("name") or ""))
                caption_val = sanitize_editorial_caption(str(row.get("caption") or row.get("description") or ""))
                alt_val = sanitize_editorial_caption(str(row.get("alt_text") or row.get("alt") or caption_val or title_val))

                item = DAMMediaItem(
                    asset_id=str(row.get("asset_id") or row.get("id") or f"dam-{idx + 1}"),
                    file_path=file_path,
                    city=str(row.get("city") or row.get("location") or "").strip(),
                    region=str(row.get("region") or row.get("state") or "").strip(),
                    country=str(row.get("country") or "").strip(),
                    title=title_val,
                    caption=caption_val,
                    alt_text=alt_val,
                    keywords=kw_list[:14],
                    sha256=sha_val,
                    public_url=str(row.get("public_url") or row.get("cdn_url") or row.get("url") or "").strip(),
                )
                items.append(item)
        except Exception as exc:
            logger.warning("Failed to parse TravelMediaDAM catalog '%s': %s", self.catalog_path, exc)
            return []

        return items

    def query_media(
        self,
        city: str = "",
        region: str = "",
        country: str = "",
        topic: str = "",
        limit: int = 3,
    ) -> list[DAMMediaItem]:
        """Query authentic DAM assets matching destination/topic with SHA-256 & stem deduplication and donkey ban filtering."""
        catalog = self.load_catalog()
        if not catalog or limit <= 0:
            return []

        query_tokens = [
            tok.lower()
            for tok in re.split(r"[\s,/-]+", f"{city} {region} {country} {topic}".strip())
            if len(tok) >= 3 and tok.lower() not in {"the", "and", "for", "with", "guide", "best", "top", "things"}
        ]

        scored: list[tuple[int, DAMMediaItem]] = []
        seen_sha256: set[str] = set()
        seen_stems: set[str] = set()

        for item in catalog:
            if is_prohibited_donkey_media(item, country=country):
                continue

            stem = Path(item.file_path).stem.lower()
            sha = item.sha256 or compute_file_sha256(item.file_path)
            if sha in seen_sha256 or stem in seen_stems:
                continue

            score = 0
            if city and item.city.lower() == city.strip().lower():
                score += 10
            elif city and city.strip().lower() in item.city.lower():
                score += 6

            if country and item.country.lower() == country.strip().lower():
                score += 5
            if region and item.region.lower() == region.strip().lower():
                score += 4

            searchable = " ".join(
                [item.city, item.region, item.country, item.title, item.caption, " ".join(item.keywords)]
            ).lower()
            for tok in query_tokens:
                if tok in searchable:
                    score += 2

            if score > 0 or not query_tokens:
                seen_sha256.add(sha)
                seen_stems.add(stem)
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]
