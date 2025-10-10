from gmail_chat.config import get_settings


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("VECTOR_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.google_client_id == ""
    assert settings.vector_store_dir == tmp_path
