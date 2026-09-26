from types import SimpleNamespace
from hashlib import sha256
import re
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import get_db
from app.auth import get_current_user
from app.services import conversation_flow_admin
from app.services.conversation_flow_admin import (
    ConversationFlowAdminClient,
    FlowAdminAPIError,
    FlowAdminConfigurationError,
    flow_admin_client,
)


ADMIN_ID = "00000000-0000-0000-0000-000000000123"


def contract_payload():
    return {
        "events": [
            {
                "event_key": "dashboard.link.sent",
                "variables": ["login_url", "ttl_minutes"],
                "actions": [],
                "terminal_only": True,
            },
            {
                "event_key": "category.confirmation_required",
                "variables": ["category"],
                "actions": ["confirm_category", "reject_category"],
                "terminal_only": False,
            },
        ],
        "node_types": ["text", "reply_button", "list"],
    }


def flow_payload():
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "slug": "dashboard-link",
        "name": "Enlace al dashboard",
        "event_key": "dashboard.link.sent",
        "status": "active",
        "draft": {
            "id": "22222222-2222-2222-2222-222222222222",
            "version_number": 1,
            "definition": {
                "start_node": "done",
                "nodes": [
                    {
                        "id": "done",
                        "type": "text",
                        "body": "Entrá en {login_url}",
                        "terminal": True,
                    }
                ],
            },
        },
        "published": None,
        "versions": [],
    }


@pytest.fixture(autouse=True)
def admin_environment(monkeypatch):
    monkeypatch.setenv("FLOW_ADMIN_AUTH_USER_IDS", ADMIN_ID)
    monkeypatch.setenv("LUKA_BACKEND_URL", "https://backend.example")
    monkeypatch.setenv("FLOW_ADMIN_API_KEY", "server-only-key")


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: ADMIN_ID

    def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        "app.main.get_user_by_auth_id",
        lambda _db, _auth_user_id: SimpleNamespace(whatsapp_id="5491100000000"),
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_page_requires_allowlisted_authenticated_user(client, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: "not-an-admin"
    list_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(flow_admin_client, "list", list_mock)

    response = client.get("/admin/flujos")

    assert response.status_code == 403
    list_mock.assert_not_awaited()


def test_admin_page_lists_flows_without_exposing_backend_key(client, monkeypatch):
    monkeypatch.setattr(
        flow_admin_client,
        "list",
        AsyncMock(return_value=[flow_payload()]),
    )

    response = client.get("/admin/flujos")

    assert response.status_code == 200
    assert "Enlace al dashboard" in response.text
    assert "Borrador" in response.text
    assert "server-only-key" not in response.text


def test_editor_receives_closed_contract_from_backend(client, monkeypatch):
    monkeypatch.setattr(
        flow_admin_client,
        "contracts",
        AsyncMock(return_value=contract_payload()),
    )

    response = client.get("/admin/flujos/nuevo")

    assert response.status_code == 200
    assert "category.confirmation_required" in response.text
    assert "confirm_category" in response.text
    assert "FLOW_ADMIN_API_KEY" not in response.text


def test_flow_pages_load_content_versioned_assets(client, monkeypatch):
    monkeypatch.setattr(
        flow_admin_client, "contracts", AsyncMock(return_value=contract_payload())
    )
    monkeypatch.setattr(flow_admin_client, "list", AsyncMock(return_value=[]))
    editor = client.get("/admin/flujos/nuevo")
    listing = client.get("/admin/flujos")

    paths = [
        "css/admin_flows.css",
        "js/admin_flow_graph.js",
        "js/admin_flows.js",
    ]
    for path in paths:
        urls = re.findall(rf"/static/{re.escape(path)}\?v=[a-f0-9]+", editor.text)
        assert len(urls) == 1
        asset = client.get(urls[0])
        assert asset.status_code == 200
        assert urls[0].endswith(sha256(asset.content).hexdigest()[:16])
        if path.endswith(".css"):
            assert urls[0] in listing.text

    assert editor.text.index("admin_flow_graph.js?") < editor.text.index(
        "admin_flows.js?"
    )


def test_create_proxy_forwards_mutation_to_backend_client(client, monkeypatch):
    create_mock = AsyncMock(return_value=flow_payload())
    monkeypatch.setattr(flow_admin_client, "create", create_mock)
    payload = {
        "slug": "dashboard-link",
        "name": "Enlace al dashboard",
        "event_key": "dashboard.link.sent",
        "definition": flow_payload()["draft"]["definition"],
    }

    response = client.post("/admin/flujos/api", json=payload)

    assert response.status_code == 201
    create_mock.assert_awaited_once_with(payload)


def test_save_draft_proxy_forwards_only_to_backend_client(client, monkeypatch):
    save_mock = AsyncMock(return_value=flow_payload())
    monkeypatch.setattr(flow_admin_client, "save_draft", save_mock)
    payload = {
        "name": "Enlace actualizado",
        "definition": flow_payload()["draft"]["definition"],
    }

    response = client.put(
        f"/admin/flujos/api/{flow_payload()['id']}/borrador",
        json=payload,
    )

    assert response.status_code == 200
    save_mock.assert_awaited_once_with(flow_payload()["id"], payload)


@pytest.mark.parametrize(
    ("method_name", "http_method", "path_suffix"),
    [
        ("discard_draft", "delete", "borrador"),
        ("publish", "post", "publicar"),
        ("archive", "post", "retirar"),
    ],
)
def test_lifecycle_proxies_use_backend_api(
    client,
    monkeypatch,
    method_name,
    http_method,
    path_suffix,
):
    operation = AsyncMock(return_value=flow_payload())
    monkeypatch.setattr(flow_admin_client, method_name, operation)
    flow_id = flow_payload()["id"]

    response = getattr(client, http_method)(
        f"/admin/flujos/api/{flow_id}/{path_suffix}"
    )

    assert response.status_code == 200
    operation.assert_awaited_once_with(flow_id)


def test_validation_errors_are_returned_without_backend_credentials(client, monkeypatch):
    monkeypatch.setattr(
        flow_admin_client,
        "validate",
        AsyncMock(
            side_effect=FlowAdminAPIError(
                422,
                "El recorrido no es válido.",
                ({"path": "nodes.0.body", "message": "campo requerido"},),
            )
        ),
    )

    response = client.post(
        "/admin/flujos/api/validar",
        json={"event_key": "dashboard.link.sent", "definition": {}},
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["path"] == "nodes.0.body"
    assert "server-only-key" not in response.text


@pytest.mark.asyncio
async def test_backend_client_keeps_bearer_key_server_side(monkeypatch):
    captured = {}

    def handler(request: httpx.Request):
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"events": [], "node_types": []})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        conversation_flow_admin.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(transport=transport, **kwargs),
    )

    result = await ConversationFlowAdminClient().contracts()

    assert result == {"events": [], "node_types": []}
    assert captured["authorization"] == "Bearer server-only-key"


@pytest.mark.asyncio
async def test_backend_client_requires_complete_server_configuration(monkeypatch):
    monkeypatch.delenv("FLOW_ADMIN_API_KEY")

    with pytest.raises(FlowAdminConfigurationError):
        await ConversationFlowAdminClient().list()
