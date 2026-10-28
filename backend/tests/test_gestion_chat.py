import re
import json
from uuid import uuid4
from urllib.request import Request

import pytest

from ctg_go.api.errors import ApiError
from ctg_go.modules.gestions.assistant import _NoRedirectHandler, request_assistant_reply
from ctg_go.modules.gestions.schemas import GestionMessageCreateRequest


def test_gestion_code_is_generated_automatically(client, auth_header):
    response = client.post(
        "/api/v1/gestions",
        headers=auth_header("op1"),
        json={"client_id": client.app.state.seed_ids["client1"], "code": "MANUAL"},
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
                "expected_version": cpes[0]["version"],
                "fields": {"grano": "Soja"},
            },
            {
                "cpe_id": None,
                "title": "Nueva carta de maíz",
                "fields": {"grano": "Maíz"},
            },
        ]

    monkeypatch.setattr(
        "ctg_go.modules.gestions.use_cases.request_assistant_reply",
        fake_assistant_reply,
    )
    gestion_id = client.app.state.seed_ids["gestion1"]
    response = client.post(
        f"/api/v1/gestions/{gestion_id}/messages",
        headers=auth_header("op1"),
        json={
            "content": "Es una carta de soja",
            "attachment": {
                "filename": "foto.png",
                "media_type": "image/png",
                "content_base64": "Y2FydGE=",
            },
        },
    )

    assert response.status_code == 201
    assert [message["role"] for message in response.json()] == ["user", "assistant"]
    assert response.json()[0]["attachment_name"] == "foto.png"
    assert "content_base64" not in response.json()[0]
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
        "output_text": json.dumps({
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
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(provider_response).encode()

    captured_request = {}

    def fake_open(request, timeout):
        assert request.get_header("Authorization") == ("Bearer " + "test-token")
        assert timeout == 45
        assert request.full_url == "https://api.openai.com/v1/responses"
        captured_request.update(json.loads(request.data))
        return FakeResponse()

    class FakeOpener:
        def open(self, request, timeout):
            return fake_open(request, timeout)

    def fake_build_opener(handler):
        assert isinstance(handler, _NoRedirectHandler)
        return FakeOpener()

    monkeypatch.setenv("TOKEN_IA", "test-token")
    monkeypatch.setattr("ctg_go.modules.gestions.assistant.build_opener", fake_build_opener)
    reply, suggestions = request_assistant_reply(
        GestionMessageCreateRequest(
            content="Es soja",
            attachment={
                "filename": "carta.png",
                "media_type": "image/png",
                "content_base64": "Y2FydGE=",
            },
        ),
        messages=[],
        cpes=[{"id": cpe_id, "title": "Carta", "status": "draft", "version": 2, "fields": {}}],
    )

    image_url = captured_request["input"][-1]["content"][1]["image_url"]
    assert image_url == "data:image/png;base64,Y2FydGE="
    assert captured_request["text"]["format"] == {"type": "json_object"}
    assert reply == "Encontré datos."
    assert suggestions == [{
        "cpe_id": cpe_id,
        "title": "Carta",
        "expected_version": 2,
        "fields": {"grano": "Soja"},
    }]


def test_assistant_redirect_handler_rejects_redirects():
    handler = _NoRedirectHandler()
    request = Request("https://provider.example/v1/chat/completions")

    assert handler.redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://other.example/collect",
    ) is None


def test_assistant_rejects_invalid_image(monkeypatch):
    monkeypatch.setenv("TOKEN_IA", "test-token")
    with pytest.raises(ApiError) as error:
        request_assistant_reply(
            GestionMessageCreateRequest(
                content="Analizá esta imagen",
                attachment={
                    "filename": "carta.png",
                    "media_type": "image/png",
                    "content_base64": "not base64!",
                },
            ),
            messages=[],
            cpes=[],
        )
    assert error.value.status_code == 422


def test_assistant_sends_pdf_to_responses_api(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps({"output_text": '{"reply":"PDF leído","suggestions":[]}'}).encode()

    captured_request = {}

    class FakeOpener:
        def open(self, request, timeout):
            captured_request.update(json.loads(request.data))
            return FakeResponse()

    monkeypatch.setenv("TOKEN_IA", "test-token")
    monkeypatch.setattr("ctg_go.modules.gestions.assistant.build_opener", lambda *_: FakeOpener())
    reply, suggestions = request_assistant_reply(
        GestionMessageCreateRequest(
            content="Completá la carta",
            attachment={
                "filename": "carta.pdf",
                "media_type": "application/pdf",
                "content_base64": "JVBERg==",
            },
        ),
        messages=[],
        cpes=[],
    )

    pdf_input = captured_request["input"][-1]["content"][1]
    assert pdf_input["type"] == "input_file"
    assert pdf_input["filename"] == "carta.pdf"
    assert pdf_input["file_data"] == "data:application/pdf;base64,JVBERg=="
    assert reply == "PDF leído"
    assert suggestions == []


def test_assistant_transcribes_audio_before_extracting_fields(monkeypatch):
    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return self.body

    captured_request = {}

    class FakeOpener:
        def open(self, request, timeout):
            if request.full_url.endswith("/audio/transcriptions"):
                assert timeout == 60
                assert request.get_header("Authorization") == "Bearer test-token"
                assert b'name="model"\r\n\r\ngpt-4o-mini-transcribe' in request.data
                assert b'filename="audio__.mp3"' in request.data
                return FakeResponse(b'{"text":"La carta es de soja"}')
            assert request.full_url.endswith("/responses")
            captured_request.update(json.loads(request.data))
            return FakeResponse(b'{"output_text":"{\\"reply\\":\\"Audio interpretado\\",\\"suggestions\\":[]}"}')

    monkeypatch.setenv("TOKEN_IA", "test-token")
    monkeypatch.setattr("ctg_go.modules.gestions.assistant.build_opener", lambda *_: FakeOpener())
    reply, suggestions = request_assistant_reply(
        GestionMessageCreateRequest(
            content="",
            attachment={
                "filename": 'audio";.mp3',
                "media_type": "audio/mpeg",
                "content_base64": "YXVkaW8=",
            },
        ),
        messages=[],
        cpes=[],
    )

    assert captured_request["input"][-1]["content"][1]["text"] == "Transcripción del audio: La carta es de soja"
    assert reply == "Audio interpretado"
    assert suggestions == []
