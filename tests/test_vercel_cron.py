from fastapi.testclient import TestClient

from api.index import Config, GitHubActionManager, app


def test_podcast_cron_requires_bearer_secret(monkeypatch):
    monkeypatch.setattr(Config, "CRON_SECRET", "cron-secret")

    async def fail_dispatch(*args, **kwargs):
        raise AssertionError("dispatch should not be called without authorization")

    monkeypatch.setattr(GitHubActionManager, "dispatch", fail_dispatch)

    response = TestClient(app).get("/api/cron/podcast-scanner")

    assert response.status_code == 401


def test_podcast_cron_dispatches_existing_workflow(monkeypatch):
    monkeypatch.setattr(Config, "CRON_SECRET", "cron-secret")
    captured = {}

    async def fake_dispatch(workflow_file, inputs, timeout=10.0):
        captured["workflow_file"] = workflow_file
        captured["inputs"] = inputs
        captured["timeout"] = timeout
        return True

    monkeypatch.setattr(GitHubActionManager, "dispatch", fake_dispatch)

    response = TestClient(app).get(
        "/api/cron/podcast-scanner",
        headers={"Authorization": "Bearer cron-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "workflow": "podcast-scanner.yml"}
    assert captured == {
        "workflow_file": "podcast-scanner.yml",
        "inputs": {},
        "timeout": 10.0,
    }


def test_podcast_cron_reports_missing_secret(monkeypatch):
    monkeypatch.setattr(Config, "CRON_SECRET", "")

    response = TestClient(app).get(
        "/api/cron/podcast-scanner",
        headers={"Authorization": "Bearer cron-secret"},
    )

    assert response.status_code == 500
