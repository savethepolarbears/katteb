import json

import pytest

from katteb.config import KattebConfig


def test_config_from_explicit_key():
    cfg = KattebConfig(api_key="test_explicit_key_123")
    assert cfg.has_api_key() is True
    assert cfg.api_key == "test_explicit_key_123"


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("KATTEB_API_KEY", "env_key_456")
    cfg = KattebConfig()
    assert cfg.api_key == "env_key_456"


def test_config_missing_raises():
    cfg = KattebConfig(api_key="")
    cfg._api_key = None
    with pytest.raises(ValueError, match="Katteb API key not configured"):
        _ = cfg.api_key


def test_save_global_api_key(tmp_path, monkeypatch):
    test_config_dir = tmp_path / ".katteb"
    test_config_file = test_config_dir / "config.json"
    monkeypatch.setattr("katteb.config.CONFIG_DIR", test_config_dir)
    monkeypatch.setattr("katteb.config.CONFIG_FILE", test_config_file)

    saved = KattebConfig.save_global_api_key("saved_key_789")
    assert saved == test_config_file
    assert test_config_file.is_file()

    with open(test_config_file) as f:
        data = json.load(f)
        assert data["api_key"] == "saved_key_789"
