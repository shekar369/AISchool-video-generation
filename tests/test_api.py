def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_stages_lists_providers(client):
    stages = client.get("/stages").json()
    assert [s["stage"] for s in stages] == ["script", "storyboard", "voice", "visuals", "assemble"]
    assert all(s["default"] == "mock" for s in stages)


def test_create_and_fetch_run(client):
    resp = client.post("/runs", json={"topic": "The water cycle"})
    assert resp.status_code == 202
    run_id = resp.json()["id"]

    # TestClient runs background tasks before returning, so the run is already done.
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "completed"
    assert run["output_path"].endswith("manifest.json")
    assert [r["id"] for r in client.get("/runs").json()] == [run_id]


def test_unknown_provider_returns_422(client):
    resp = client.post("/runs", json={"topic": "Gravity", "providers": {"voice": "nope"}})
    assert resp.status_code == 422


def test_missing_run_returns_404(client):
    assert client.get("/runs/20260101-000000-abcdef").status_code == 404
    assert client.get("/runs/..%2Fetc").status_code == 404


def test_resume_requires_failed_run(client):
    run_id = client.post("/runs", json={"topic": "Gravity"}).json()["id"]
    assert client.post(f"/runs/{run_id}/resume").status_code == 409
