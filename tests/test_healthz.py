from fastapi.testclient import TestClient

from nc_parser.api.main import create_app


def test_healthz() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


