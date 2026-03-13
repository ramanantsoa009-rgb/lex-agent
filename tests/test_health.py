from fastapi.testclient import TestClient
from lex_agent import app

client = TestClient(app)


def test_docs_accessible():
    """Verifie que la page /docs repond"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    """Verifie que le schema OpenAPI est genere"""
    response = client.get("/openapi.json")
    assert response.status_code == 200