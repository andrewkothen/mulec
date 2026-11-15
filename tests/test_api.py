import time
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from backend.api.app import create_app
from backend.fixtures import make_demo


def wait_job(client, job_id):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            assert job["status"] == "done", job
            return job
        time.sleep(0.1)
    raise AssertionError("Local analysis timed out")


def test_complete_import_edit_save_reload_export(tmp_path):
    fixture = make_demo(tmp_path / "test.wav")
    with TestClient(create_app(tmp_path / "data")) as client:
        with fixture.open("rb") as file:
            response = client.post(
                "/api/analyze",
                files={"file": ("test.wav", file, "audio/wav")},
                data={"title": "My rehearsal"},
            )
        assert response.status_code == 202, response.text
        job = wait_job(client, response.json()["id"])
        project_id = job["project_id"]
        p = client.get(f"/api/projects/{project_id}").json()
        assert p["measures"]
        p["measures"][0]["chords"][0].update(symbol="Bbmaj7/F", manual=True)
        save = client.put(f"/api/projects/{project_id}", json=p)
        assert save.status_code == 200, save.text
        assert client.put(f"/api/projects/{project_id}", json=p).status_code == 409
        p = client.get(f"/api/projects/{project_id}").json()
        assert p["measures"][0]["chords"][0]["symbol"] == "Bbmaj7/F"
        audio = client.get(f"/api/projects/{project_id}/audio", headers={"Range": "bytes=0-100"})
        assert audio.status_code == 206
        for format in ("pdf", "musicxml", "json"):
            result = client.post(f"/api/export/{format}?part=bb", json=p)
            assert result.status_code == 200, result.text[:300]
            if format == "pdf":
                assert result.content.startswith(b"%PDF")
            elif format == "musicxml":
                assert ET.fromstring(result.content).findtext(".//harmony/root/root-step") == "C"
        imported = client.post("/api/projects/import", json=p)
        assert imported.status_code == 200
        assert imported.json()["id"] != project_id
        assert client.get(f"/api/projects/{imported.json()['id']}/audio").status_code == 404
        p["measures"][0]["chords"][0]["symbol"] = "garbage"
        assert client.put(f"/api/projects/{project_id}", json=p).status_code == 422
    # Restart persistence; analysis never overwrites edits.
    with TestClient(create_app(tmp_path / "data")) as client:
        assert (
            client.get(f"/api/projects/{project_id}").json()["measures"][0]["chords"][0]["symbol"]
            == "Bbmaj7/F"
        )


def test_api_boundaries_and_reference_workflow(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/health").json()["local_only"]
        assert client.get("/api/projects/missing").status_code == 404
        assert client.get("/api/projects", headers={"origin": "https://example.com"}).status_code == 403
        assert client.get("/api/projects", headers={"host": "evil.example"}).status_code == 400
        assert client.post("/api/analyze", files={"file": ("x.txt", b"hello")}).status_code == 422
        assert (
            client.post(
                "/api/analyze", files={"file": ("x.wav", b"bad")}, data={"reference": "https://evil.example"}
            ).status_code
            == 422
        )
