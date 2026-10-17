import re
import json
from uuid import uuid4

from ctg_go.modules.gestions.assistant import request_assistant_reply
from ctg_go.modules.gestions.schemas import GestionMessageCreateRequest


def test_gestion_code_is_generated_automatically(client, auth_header):
    response = client.post(
        "/api/v1/gestions",
        headers=auth_header("op1"),
        json={"client_id": client.app.state.seed_ids["client1"]},
    )

    assert response.status_code == 201
    assert re.fullmatch(r"GES-[A-F0-9]{32}", response.json()["code"])


def test_chat_is_persisted_and_scoped_to_gestion(client, auth_header, monkeypatch):
    def fake_assistant_reply(payload, *, messages, cpes):
        assert messages == []
        assert cpes[0]["id"] == client.app.state.seed_ids["cpe1"]
        return "Encontré el grano.", [
            {
                "cpe_id": cpes[0]["id"],
                "title": "Borrador",
                "fields": {"grano": "Soja"},
            },
            {
                "cpe_id": None,
                "title": "Nueva carta de maíz",
                "fields": {"grano": "Maíz"},
            },
        ]

    monkeypatch.setattr(
        "ctg_go.modules.gestions.router.request_assistant_reply",
        fake_assistant_reply,
    )
    gestion_id = client.app.state.seed_ids["gestion1"]
    response = client.post(
        f"/api/v1/gestions/{gestion_id}/messages",
        headers=auth_header("op1"),
        json={"content": "Es una carta de soja"},
    )

    assert response.status_code == 201
    assert [message["role"] for message in response.json()] == ["user", "assistant"]
    assert response.json()[1]["suggestions"][0]["fields"] == {"grano": "Soja"}
    assistant_id = response.json()[1]["id"]
    apply_url = f"/api/v1/gestions/{gestion_id}/messages/{assistant_id}/suggestions"
    applied = client.post(f"{apply_url}/0/apply", headers=auth_header("op1"))
    assert applied.status_code == 200
    assert applied.json()["payload_json"]["cpe"]["grano"] == "Soja"
    assert applied.json()["payload_json"]["field_status"]["grano"] == "ai"
    assert applied.json()["version"] == 3

    applied_again = client.post(f"{apply_url}/0/apply", headers=auth_header("op1"))
    assert applied_again.json()["id"] == applied.json()["id"]
    assert applied_again.json()["version"] == 3

    new_draft = client.post(f"{apply_url}/1/apply", headers=auth_header("op1"))
    assert new_draft.status_code == 200
    assert new_draft.json()["title"] == "Nueva carta de maíz"
    assert new_draft.json()["payload_json"]["cpe"]["grano"] == "Maíz"

    history = client.get(
        f"/api/v1/gestions/{gestion_id}/messages",
        headers=auth_header("op1"),
    )
    assert [message["content"] for message in history.json()] == ["Es una carta de soja", "Encontré el grano."]
    assert history.json()[1]["suggestions"][0]["applied"] is True

    forbidden = client.get(
        f"/api/v1/gestions/{gestion_id}/messages",
        headers=auth_header("admin2"),
    )
    assert forbidden.status_code == 404


def test_chat_requires_configured_ai_provider(client, auth_header, monkeypatch):
    monkeypatch.delenv("TOKEN_AI", raising=False)
    monkeypatch.delenv("TOKEN_IA", raising=False)
    response = client.post(
        f"/api/v1/gestions/{client.app.state.seed_ids['gestion1']}/messages",
        headers=auth_header("op1"),
        json={"content": "Completar la carta"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "assistant_not_configured"


def test_assistant_filters_unknown_fields_and_cpe_targets(monkeypatch):
    cpe_id = str(uuid4())
    provider_response = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "reply": "Encontré datos.",
                    "suggestions": [
                        {
                            "cpe_id": cpe_id,
                            "title": "Carta",
                            "fields": {"grano": "Soja", "instruccion_inventada": "x"},
                        },
                        {
                            "cpe_id": str(uuid4()),
                            "title": "Otra carta",
                            "fields": {"grano": "Maíz"},
                        },
                    ],
                }),
            },
        }],
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(provider_response).encode()

    def fake_urlopen(request, timeout):
        assert request.get_header("Authorization") == ("Bearer " + "test-token")
        assert timeout == 45
        return FakeResponse()

    monkeypatch.setenv("TOKEN_IA", "test-token")
    monkeypatch.setattr("ctg_go.modules.gestions.assistant.urlopen", fake_urlopen)
    reply, suggestions = request_assistant_reply(
        GestionMessageCreateRequest(content="Es soja"),
        messages=[],
        cpes=[{"id": cpe_id, "title": "Carta", "status": "draft", "fields": {}}],
    )

    assert reply == "Encontré datos."
    assert suggestions == [{
        "cpe_id": cpe_id,
        "title": "Carta",
        "fields": {"grano": "Soja"},
    }]
