"""Tests for profile export/import endpoints in k2deck.web.routes.profiles."""

import json
from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient

from k2deck.web.server import app

VALID_CONFIG = {
    "profile_name": "test-profile",
    "mappings": {
        "note_on": {"36": {"action": "hotkey", "keys": ["f1"]}},
        "cc": {},
    },
}


class TestExportProfile:
    def setup_method(self):
        self.client = TestClient(app)

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_export_existing_profile(self, mock_dir, tmp_path):
        """GET /api/profiles/{name}/export returns JSON file download."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name
        mock_dir.exists.return_value = True

        # Create a profile file
        profile_path = tmp_path / "gaming.json"
        profile_path.write_text(json.dumps(VALID_CONFIG), encoding="utf-8")

        resp = self.client.get("/api/profiles/gaming/export")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert "k2deck-gaming.json" in resp.headers.get("content-disposition", "")
        assert resp.json()["profile_name"] == "test-profile"

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_export_missing_profile_404(self, mock_dir, tmp_path):
        """GET /api/profiles/{name}/export returns 404 for missing profile."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name

        resp = self.client.get("/api/profiles/nonexistent/export")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]


class TestImportProfile:
    def setup_method(self):
        self.client = TestClient(app)

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_import_valid_profile(self, mock_dir, tmp_path):
        """POST /api/profiles/import creates new profile from uploaded JSON."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name
        mock_dir.exists.return_value = True
        mock_dir.mkdir = lambda **kw: None

        content = json.dumps(VALID_CONFIG).encode("utf-8")
        resp = self.client.post(
            "/api/profiles/import",
            files={
                "file": (
                    "k2deck-test-profile.json",
                    BytesIO(content),
                    "application/json",
                )
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"] == "test-profile"
        assert "imported" in data["message"]

        # Verify file was created
        saved = tmp_path / "test-profile.json"
        assert saved.exists()
        assert json.loads(saved.read_text())["profile_name"] == "test-profile"

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_import_duplicate_name_409(self, mock_dir, tmp_path):
        """POST /api/profiles/import returns 409 if profile already exists."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name
        mock_dir.exists.return_value = True

        # Pre-create the profile
        (tmp_path / "test-profile.json").write_text("{}", encoding="utf-8")

        content = json.dumps(VALID_CONFIG).encode("utf-8")
        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("upload.json", BytesIO(content), "application/json")},
        )

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_import_non_json_extension_400(self):
        """POST /api/profiles/import rejects non-.json files."""
        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("profile.txt", BytesIO(b"{}"), "text/plain")},
        )

        assert resp.status_code == 400
        assert ".json" in resp.json()["detail"]

    def test_import_invalid_json_400(self):
        """POST /api/profiles/import rejects invalid JSON."""
        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("bad.json", BytesIO(b"not json"), "application/json")},
        )

        assert resp.status_code == 400
        assert "Invalid JSON" in resp.json()["detail"]

    def test_import_non_object_json_400(self):
        """POST /api/profiles/import rejects JSON that isn't an object."""
        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("array.json", BytesIO(b"[1,2,3]"), "application/json")},
        )

        assert resp.status_code == 400
        assert "JSON object" in resp.json()["detail"]

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_import_name_from_name_field(self, mock_dir, tmp_path):
        """POST /api/profiles/import falls back to 'name' field."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name
        mock_dir.exists.return_value = True
        mock_dir.mkdir = lambda **kw: None

        config = {"name": "my-profile", "mappings": {"note_on": {}, "cc": {}}}
        content = json.dumps(config).encode("utf-8")

        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("upload.json", BytesIO(content), "application/json")},
        )

        assert resp.status_code == 200
        assert resp.json()["profile"] == "my-profile"

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_import_name_from_filename(self, mock_dir, tmp_path):
        """POST /api/profiles/import derives name from filename when no name in config."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name
        mock_dir.exists.return_value = True
        mock_dir.mkdir = lambda **kw: None

        config = {"mappings": {"note_on": {}, "cc": {}}}
        content = json.dumps(config).encode("utf-8")

        resp = self.client.post(
            "/api/profiles/import",
            files={
                "file": ("k2deck-streaming.json", BytesIO(content), "application/json")
            },
        )

        assert resp.status_code == 200
        assert resp.json()["profile"] == "streaming"

    def test_import_file_too_large_400(self):
        """POST /api/profiles/import rejects files over 1MB."""
        large = b"{" + b'"x":' + b'"a"' * 500000 + b"}"
        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("big.json", BytesIO(large), "application/json")},
        )

        assert resp.status_code == 400
        assert "too large" in resp.json()["detail"]

    @patch("k2deck.web.routes.profiles.CONFIG_DIR")
    def test_import_invalid_profile_name_400(self, mock_dir, tmp_path):
        """POST /api/profiles/import rejects invalid profile names."""
        mock_dir.__truediv__ = lambda self, name: tmp_path / name

        config = {"profile_name": "bad name!", "mappings": {"note_on": {}, "cc": {}}}
        content = json.dumps(config).encode("utf-8")

        resp = self.client.post(
            "/api/profiles/import",
            files={"file": ("upload.json", BytesIO(content), "application/json")},
        )

        assert resp.status_code == 400
        assert "letters, numbers" in resp.json()["detail"]
