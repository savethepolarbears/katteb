"""Unit tests for TravelMediaDAM resolver, two-phase ImageMagick+ExifTool optimizer, and HTML figure injection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from katteb.cli import cli
from katteb.dam import (
    DAMMediaItem,
    TravelMediaDAMResolver,
    inject_dam_media_into_html,
    is_prohibited_donkey_media,
    optimize_media_asset,
    sanitize_editorial_caption,
    sanitize_editorial_title,
)


def test_sanitize_editorial_title_and_caption():
    raw_title = "Picturesque Oia Blue Domes at Sunset © Kyle Kroeger."
    assert sanitize_editorial_title(raw_title) == "Oia Blue Domes at Sunset"

    raw_caption = "A sun-drenched caldera view nestled in Oia. Photo by Kyle Kroeger."
    cleaned_caption = sanitize_editorial_caption(raw_caption)
    assert "Kyle Kroeger" not in cleaned_caption
    assert "©" not in cleaned_caption
    assert "nestled" not in cleaned_caption.lower()
    assert "sun-drenched" not in cleaned_caption.lower()
    assert "caldera view in Oia." in cleaned_caption


def test_is_prohibited_donkey_media():
    banned_item = DAMMediaItem(
        asset_id="gr-1",
        file_path="/photos/santorini_donkey_ride.jpg",
        city="Fira",
        country="Greece",
        title="Donkey ride on the Old Port steps",
        caption="Tourists riding a donkey in Fira",
    )
    assert is_prohibited_donkey_media(banned_item) is True

    allowed_item = DAMMediaItem(
        asset_id="gr-2",
        file_path="/photos/santorini_cable_car.jpg",
        city="Fira",
        country="Greece",
        title="Fira Cable Car over Caldera",
        caption="The modern cable car connecting the Old Port to Fira town.",
    )
    assert is_prohibited_donkey_media(allowed_item) is False


def test_dam_resolver_csv_deduplication_and_donkey_ban(tmp_path: Path):
    csv_file = tmp_path / "places.csv"
    csv_file.write_text(
        "asset_id,file_path,city,region,country,title,caption,sha256,public_url,keywords\n"
        "1,/photos/oia_sunset_1.jpg,Oia,Cyclades,Greece,Oia Sunset © Kyle Kroeger,Sunset over Oia caldera.,sha_oia_1,https://cdn.example.com/oia1.jpg,\"santorini,sunset\"\n"
        "2,/photos/oia_sunset_1_copy.jpg,Oia,Cyclades,Greece,Duplicate Checksum Photo,Duplicate SHA.,sha_oia_1,https://cdn.example.com/oia1_dup.jpg,\"santorini\"\n"
        "3,/photos/oia_sunset_2.raw,Oia,Cyclades,Greece,Duplicate Stem Photo,Same stem as item 4.,sha_oia_2a,https://cdn.example.com/oia2.jpg,\"santorini\"\n"
        "4,/photos/oia_sunset_2.jpg,Oia,Cyclades,Greece,Duplicate Stem Photo JPEG,Same stem.,sha_oia_2b,https://cdn.example.com/oia2b.jpg,\"santorini\"\n"
        "5,/photos/fira_donkey_taxi.jpg,Fira,Cyclades,Greece,Fira Donkey Taxi,Donkeys carrying luggage in Fira.,sha_donkey,https://cdn.example.com/donkey.jpg,\"donkey,fira\"\n",
        encoding="utf-8",
    )

    resolver = TravelMediaDAMResolver(catalog_path=csv_file)
    assert resolver.is_available() is True

    results = resolver.query_media(city="Oia", country="Greece", topic="Santorini Sunset", limit=5)
    assert len(results) == 2
    assert results[0].asset_id == "1"
    assert "Kyle Kroeger" not in results[0].title
    assert all("donkey" not in r.file_path for r in results)


def test_dam_resolver_offline_graceful_fallback(tmp_path: Path):
    missing_csv = tmp_path / "unmounted_volume" / "places.csv"
    resolver = TravelMediaDAMResolver(catalog_path=missing_csv, originals_dir=tmp_path / "unmounted_orig")
    assert resolver.is_available() is False
    assert resolver.query_media(city="Berlin", country="Germany") == []


def test_optimize_media_asset_two_phase_sequence(tmp_path: Path):
    src_img = tmp_path / "munich_marienplatz.jpg"
    src_img.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 1024)
    out_dir = tmp_path / "optimized"

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "magick":
            dst_path = Path(cmd[-1])
            dst_path.write_bytes(b"\xff\xd8\xff\xe0" + b"1" * 4096)
        res = MagicMock()
        res.returncode = 0
        res.stdout = "1 image files updated"
        res.stderr = ""
        return res

    with patch("katteb.dam.subprocess.run", side_effect=fake_run):
        result = optimize_media_asset(
            src_path=src_img,
            output_dir=out_dir,
            title="Picturesque Marienplatz in Munich © Kyle Kroeger.",
            caption="Town hall tower in central Munich. Photo by Kyle Kroeger.",
            city="Munich",
            country="Germany",
        )

    assert result["success"] is True
    assert result["bytes_size"] < 1_000_000
    assert result["title"] == "Marienplatz in Munich"
    assert "Kyle Kroeger" not in result["caption"]
    assert len(calls) == 2
    assert calls[0][0] == "magick"
    assert "2048x2048>" in calls[0]
    assert "-strip" in calls[0]
    assert calls[1][0] == "exiftool"
    assert "-Creator=Kyle Kroeger" in calls[1]
    assert "-CopyrightNotice=© Kyle Kroeger" in calls[1]


def test_optimize_media_asset_rejects_oversized_and_donkey(tmp_path: Path):
    src_img = tmp_path / "santorini_photo.jpg"
    src_img.write_bytes(b"rawbytes")

    with pytest.raises(ValueError, match="donkey"):
        optimize_media_asset(
            src_path=src_img,
            output_dir=tmp_path / "out",
            title="Santorini Donkey Ride",
            country="Greece",
        )

    def fake_oversize_run(cmd, **kwargs):
        if cmd[0] == "magick":
            Path(cmd[-1]).write_bytes(b"x" * 1_200_000)
        res = MagicMock()
        res.returncode = 0
        res.stdout = ""
        res.stderr = ""
        return res

    with patch("katteb.dam.subprocess.run", side_effect=fake_oversize_run):
        with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
            optimize_media_asset(
                src_path=src_img,
                output_dir=tmp_path / "out",
                title="Caldera Cliffs",
                country="Greece",
                max_bytes=1_000_000,
            )


def test_inject_dam_media_into_html():
    html_doc = (
        "<h2>Overview of Amsterdam Canals</h2>"
        "<p>The historic canal ring was built in the 17th century.</p>"
        "<h2>Best Jordaan Cafes</h2>"
        "<p>Explore local brown cafes along the Prinsengracht.</p>"
    )
    items = [
        DAMMediaItem(
            asset_id="nl-1",
            file_path="/photos/prinsengracht.jpg",
            city="Amsterdam",
            country="Netherlands",
            title="Prinsengracht Canal Houses © Kyle Kroeger.",
            caption="Historic gable houses along the Prinsengracht canal in Amsterdam. © Kyle Kroeger",
            public_url="https://images.viatravelers.com/prinsengracht.jpg",
        ),
        DAMMediaItem(
            asset_id="nl-2",
            file_path="/photos/jordaan.jpg",
            city="Amsterdam",
            country="Netherlands",
            title="Jordaan Neighborhood Courtyard",
            caption="Quiet brick courtyard in the Jordaan district.",
            public_url="https://images.viatravelers.com/jordaan.jpg",
        ),
    ]

    enriched = inject_dam_media_into_html(html_doc, items, max_images=2)
    assert enriched.count("katteb-dam-media") == 2
    assert "https://images.viatravelers.com/prinsengracht.jpg" in enriched
    assert "https://images.viatravelers.com/jordaan.jpg" in enriched
    assert "Kyle Kroeger" not in enriched


def test_cli_dam_search_and_optimize(tmp_path: Path):
    json_catalog = tmp_path / "catalog.json"
    json_catalog.write_text(
        json.dumps(
            [
                {
                    "asset_id": "it-10",
                    "file_path": "/photos/tuscany_villa.jpg",
                    "city": "Florence",
                    "country": "Italy",
                    "title": "Tuscan Hillside Villa",
                    "caption": "Stone villa surrounded by olive groves in Florence.",
                    "public_url": "https://cdn.example.com/tuscany.jpg",
                }
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(cli, ["dam", "search", "--city", "Florence", "--catalog", str(json_catalog), "--json"])
    assert res.exit_code == 0
    payload = json.loads(res.output)
    assert payload["count"] == 1
    assert payload["items"][0]["asset_id"] == "it-10"


def test_expand_post_with_dam_media_injection(tmp_path: Path, monkeypatch):
    from katteb.client import KattebClient
    from katteb.models import ArticleGetResponse
    from katteb.wordpress import WordPressFleetManager

    monkeypatch.setenv("KATTEB_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("KATTEB_TELEMETRY_FILE", str(tmp_path / "telemetry.jsonl"))

    catalog_file = tmp_path / "dam.json"
    catalog_file.write_text(
        json.dumps(
            [
                {
                    "asset_id": "fr-1",
                    "file_path": "/photos/eiffel_tower.jpg",
                    "city": "Paris",
                    "country": "France",
                    "title": "Eiffel Tower from Trocadero © Kyle Kroeger.",
                    "caption": "Morning view of the Eiffel Tower from Place du Trocadero.",
                    "public_url": "https://cdn.paristopten.com/eiffel.jpg",
                }
            ]
        ),
        encoding="utf-8",
    )

    mgr = WordPressFleetManager(KattebClient(api_key="test_key"))
    mock_post = {
        "id": 301,
        "title": "Best Paris Viewpoints",
        "post_type": "destinations",
        "status": "publish",
        "word_count": 250,
        "content": "<p>Short Paris viewpoint list.</p>",
        "meta": {"city": "Paris", "country": "France"},
    }
    valid_html = (
        "<h2>Top Viewpoints in Paris</h2><p>"
        + " ".join(["Place du Trocadero offers an iconic elevated perspective of the Eiffel Tower."] * 35)
        + "</p>"
        "<h2>Montmartre and Sacre-Coeur</h2><p>"
        + " ".join(["Climb the steps of Montmartre for sweeping views across central Paris."] * 35)
        + "</p>"
        "<h3>Metro Access Tips</h3><p>"
        + " ".join(["Use the Navigo Easy pass on RATP Metro Line 6 to reach Bir-Hakeim."] * 30)
        + "</p>"
    )
    mock_article = ArticleGetResponse(
        success=True,
        job_id=701,
        topic="Best Paris Viewpoints",
        status="completed",
        content_html=valid_html,
        word_count=1600,
        credits_charged=1600,
    )

    mock_preflight = MagicMock(success=True, site="paristopten", alias="@paristopten.prod", category="ok", message="OK")
    with (
        patch.object(mgr, "check_site_connectivity", return_value=mock_preflight),
        patch.object(mgr, "get_post_details", return_value=mock_post),
        patch.object(mgr.queue, "generate_and_wait", return_value=mock_article),
        patch("katteb.wordpress.run_wp_eval", return_value={"success": True, "new_word_count": 1620, "post_status": "publish"}),
    ):
        res = mgr.expand_and_update_post(
            site="paristopten",
            post_id=301,
            word_count=1500,
            inject_dam_media=True,
            dam_catalog_path=catalog_file,
            max_dam_images=2,
        )

    assert res["success"] is True
    assert res["dam_images_injected"] == 1

