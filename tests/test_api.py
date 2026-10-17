from app.stages import CHECKLIST

CONFIG = {
    "title": "What is RAG?",
    "idea": "Retrieval augmented generation grounds answers in your documents.",
    "stages": [
        {"stage": s, "provider": "stub"}
        for s in ("script", "fact_check", "slides", "voice", "render", "metadata", "upload")
    ],
}
ALL_TICKED = dict.fromkeys(CHECKLIST, True)


def start(client, config=CONFIG) -> str:
    resp = client.post("/runs", json=config)
    assert resp.status_code == 202, resp.text
    return resp.json()["id"]


def test_health_and_catalogue(client):
    assert client.get("/health").json()["status"] == "ok"
    stages = client.get("/stages").json()
    assert [s["stage"] for s in stages][0] == "capture" and len(stages) == 9
    assert {s["stage"] for s in stages if s["required"]} == {"capture", "review"}
    assert client.get("/review/checklist").json() == CHECKLIST


def test_full_flow_through_review_gate(client):
    run_id = start(client)
    # TestClient runs background tasks before returning, so the run has reached the gate.
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "awaiting_review"

    resp = client.post(f"/runs/{run_id}/approve", json={"checklist": {**ALL_TICKED, "hook": False}})
    assert resp.status_code == 422 and resp.json()["detail"]["missing"] == ["hook"]

    assert client.post(f"/runs/{run_id}/approve", json={"checklist": ALL_TICKED}).status_code == 202
    assert client.get(f"/runs/{run_id}").json()["status"] == "done"
    assert client.post(f"/runs/{run_id}/approve", json={"checklist": ALL_TICKED}).status_code == 409


def test_changes_and_redo(client):
    run_id = start(client)
    resp = client.post(
        f"/runs/{run_id}/changes", json={"notes": "Slower intro", "redo_from": "slides"}
    )
    assert resp.status_code == 202
    run = client.get(f"/runs/{run_id}").json()
    assert (
        run["status"] == "awaiting_review"
        and run["review"]["history"][0]["notes"] == "Slower intro"
    )

    assert client.post(f"/runs/{run_id}/redo", params={"from": "voice"}).status_code == 202
    assert client.post(f"/runs/{run_id}/redo", params={"from": "nope"}).status_code == 422


def test_invalid_config_returns_422(client):
    bad = {**CONFIG, "stages": [{"stage": "voice", "provider": "elevenlabs"}]}
    assert client.post("/runs", json=bad).status_code == 422
    assert client.post("/runs", json={"title": "x"}).status_code == 422  # missing idea


def test_unknown_run_returns_404(client):
    assert client.get("/runs/20260101-000000-abcdef").status_code == 404
    assert client.get("/runs/..%2Fetc").status_code == 404
    assert (
        client.post("/runs/20260101-000000-abcdef/redo", params={"from": "script"}).status_code
        == 404
    )
