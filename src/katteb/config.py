"""Configuration manager for Katteb API."""

import contextlib
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("katteb.config")

CONFIG_DIR = Path.home() / ".katteb"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_BASE_URL = "https://app.katteb.com/api/v2/"
DEFAULT_TELEMETRY_FILE = CONFIG_DIR / "telemetry.jsonl"
DEFAULT_CREDIT_ALERT_THRESHOLD = 50


class KattebConfig:
    """Manages Katteb API configuration from environment, files, and arguments."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        telemetry_file: Path | str | None = None,
        credit_alert_threshold: int | None = None,
    ):
        self.base_url = (base_url or os.getenv("KATTEB_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/"
        self._api_key = api_key or self._resolve_api_key()
        self._telemetry_file = Path(telemetry_file) if telemetry_file else self._resolve_telemetry_file()
        self._credit_alert_threshold = (
            credit_alert_threshold
            if credit_alert_threshold is not None
            else self._resolve_credit_alert_threshold()
        )

    def _resolve_telemetry_file(self) -> Path:
        if path_env := os.getenv("KATTEB_TELEMETRY_FILE"):
            return Path(path_env).expanduser()
        if CONFIG_FILE.is_file():
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    if custom_path := data.get("telemetry_file"):
                        return Path(custom_path).expanduser()
            except (OSError, json.JSONDecodeError):
                pass
        return DEFAULT_TELEMETRY_FILE

    def _resolve_credit_alert_threshold(self) -> int:
        if thresh_env := os.getenv("KATTEB_CREDIT_ALERT_THRESHOLD"):
            try:
                return int(thresh_env)
            except ValueError:
                pass
        if CONFIG_FILE.is_file():
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    if custom_thresh := data.get("credit_alert_threshold"):
                        return int(custom_thresh)
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        return DEFAULT_CREDIT_ALERT_THRESHOLD

    @property
    def telemetry_file(self) -> Path:
        return self._telemetry_file

    @property
    def credit_alert_threshold(self) -> int:
        return self._credit_alert_threshold

    def _resolve_api_key(self) -> str | None:
        # 1. Direct environment variable
        if key := os.getenv("KATTEB_API_KEY"):
            return key.strip()

        # 2. Global ~/.katteb/config.json
        if CONFIG_FILE.is_file():
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    if key := data.get("api_key"):
                        return str(key).strip()
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Failed to read configuration file at %s: %s", CONFIG_FILE, e)

        # 3. Load from local .env or parent .env files
        load_dotenv(override=False)
        if key := os.getenv("KATTEB_API_KEY"):
            return key.strip()

        # 4. ~/.env
        home_env = Path.home() / ".env"
        if home_env.is_file():
            load_dotenv(dotenv_path=home_env, override=False)
            if key := os.getenv("KATTEB_API_KEY"):
                return key.strip()

        return None

    @property
    def api_key(self) -> str:
        if not self._api_key:
            raise ValueError(
                "Katteb API key not configured. Set KATTEB_API_KEY in your environment, "
                "or run 'katteb config set-key <YOUR_KEY>' to store in ~/.katteb/config.json"
            )
        return self._api_key

    def has_api_key(self) -> bool:
        return bool(self._api_key)

    @classmethod
    def save_global_api_key(cls, api_key: str, base_url: str | None = None) -> Path:
        """Persist API key to ~/.katteb/config.json."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Ensure secure permissions (0o700 for dir, 0o600 for file)
        with contextlib.suppress(Exception):
            os.chmod(CONFIG_DIR, 0o700)

        data = {"api_key": api_key.strip()}
        if base_url:
            data["base_url"] = base_url.strip()

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        with contextlib.suppress(Exception):
            os.chmod(CONFIG_FILE, 0o600)

        return CONFIG_FILE


def get_config(
    api_key: str | None = None,
    base_url: str | None = None,
    telemetry_file: Path | str | None = None,
    credit_alert_threshold: int | None = None,
) -> KattebConfig:
    """Factory helper to obtain a KattebConfig instance."""
    return KattebConfig(
        api_key=api_key,
        base_url=base_url,
        telemetry_file=telemetry_file,
        credit_alert_threshold=credit_alert_threshold,
    )
