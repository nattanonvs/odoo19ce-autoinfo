# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""HTTP endpoints backing the OWL chat UI.

Two JSON-RPC endpoints feed the sidebar/history, and one streaming
(``text/event-stream``) endpoint drives the live answer.

The streaming endpoint deliberately avoids ``request.env``: Odoo closes the
request cursor as soon as the controller returns, *before* the WSGI server
consumes the generator. A dedicated cursor is therefore opened inside the
generator so the ORM stays usable for the whole exchange.
"""

import json
import logging

import odoo
from odoo import fields, http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def _sse(payload):
    """Format ``payload`` as a single server-sent event."""
    return "data: %s\n\n" % json.dumps(payload, ensure_ascii=False)


def _page_context(env, payload):
    """Resolve the (optional) page context carried by a request payload."""
    model = payload.get("model")
    res_id = payload.get("res_id")
    if not model or not res_id:
        return None
    return env["od19.ai.assistant"].build_context(
        model, int(res_id), payload.get("view_type") or "form"
    )


def _stream_answer(registry, uid, context, chat_id, question, payload=None):
    """Generator yielding SSE events for one assistant answer."""
    payload = payload or {}
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, uid, context)
        chat = None
        try:
            chat = env["od19.ai.chat"].browse(chat_id)
            if not chat.exists() or chat.user_id.id != uid:
                yield _sse({"type": "error", "message": "ไม่พบบทสนทนานี้"})
                return
            page_ctx = _page_context(env, payload)
            for event in env["od19.ai.assistant"].stream(
                question, ctx=page_ctx, chat=chat
            ):
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001 - keep the stream alive
            _logger.exception("OD19 AI stream failed")
            yield _sse({"type": "error", "message": str(exc)})


class Od19AiChatController(http.Controller):
    """Backend endpoints for the OWL chat client action."""

    @http.route("/od19_ai/chat/list", type="jsonrpc", auth="user")
    def chat_list(self, **kwargs):
        chats = request.env["od19.ai.chat"].search(
            [("user_id", "=", request.env.uid)], limit=100
        )
        return [
            {
                "id": chat.id,
                "name": chat.name or "บทสนทนาใหม่",
                "create_date": fields.Datetime.to_string(chat.create_date),
            }
            for chat in chats
        ]

    @http.route("/od19_ai/chat/messages", type="jsonrpc", auth="user")
    def chat_messages(self, chat_id=None, **kwargs):
        chat = request.env["od19.ai.chat"].browse(int(chat_id or 0))
        if not chat.exists() or chat.user_id.id != request.env.uid:
            raise AccessError("ไม่พบบทสนทนานี้")
        return {
            "chat": {
                "id": chat.id,
                "name": chat.name or "บทสนทนาใหม่",
                "model_used": chat.model_used or "",
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                }
                for msg in chat.message_ids.sorted("id")
            ],
        }

    @http.route("/od19_ai/chat/create", type="jsonrpc", auth="user")
    def chat_create(self, **kwargs):
        chat = request.env["od19.ai.chat"].create({})
        return [chat.id]

    @http.route("/od19_ai/chat/delete", type="jsonrpc", auth="user")
    def chat_delete(self, chat_id=None, **kwargs):
        chat = request.env["od19.ai.chat"].browse(int(chat_id or 0))
        if not chat.exists() or chat.user_id.id != request.env.uid:
            raise AccessError("ไม่พบบทสนทนานี้")
        chat.unlink()
        return True

    @http.route("/od19_ai/draft/confirm", type="jsonrpc", auth="user")
    def draft_confirm(self, model=None, values=None, **kwargs):
        record = request.env["od19.ai.capability"].create_draft(
            (model or "").strip(), values or {}
        )
        return {"id": record.id, "name": record.display_name}

    @http.route("/od19_ai/ask", type="jsonrpc", auth="user")
    def ask(self, question=None, model=None, res_id=None,
            view_type=None, chat_id=None, **kwargs):
        assistant = request.env["od19.ai.assistant"]
        ctx = None
        if model and res_id:
            ctx = assistant.build_context(model, int(res_id), view_type or "form")
        chat = None
        if chat_id:
            candidate = request.env["od19.ai.chat"].browse(int(chat_id))
            if candidate.exists() and candidate.user_id.id == request.env.uid:
                chat = candidate
        return assistant.ask(question or "", ctx=ctx, chat=chat)

    @http.route("/od19_ai/suggest", type="jsonrpc", auth="user")
    def suggest(self, model=None, res_id=None, view_type=None, **kwargs):
        assistant = request.env["od19.ai.assistant"]
        ctx = None
        if model and res_id:
            ctx = assistant.build_context(model, int(res_id), view_type or "form")
        elif model:
            ctx = {"model": model, "view_type": view_type or "list"}
        return {"chips": assistant.suggest_actions(ctx)}

    @http.route(
        "/od19_ai/chat/stream",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def chat_stream(self, **kwargs):
        raw = request.httprequest.get_data(as_text=True)
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {}

        registry = request.registry
        uid = request.env.uid
        context = dict(request.env.context)

        generator = _stream_answer(
            registry,
            uid,
            context,
            int(payload.get("chat_id") or 0),
            (payload.get("message") or "").strip(),
            payload,
        )
        headers = [
            ("Content-Type", "text/event-stream; charset=utf-8"),
            ("Cache-Control", "no-cache"),
            # Ask Nginx to forward each event immediately instead of buffering.
            ("X-Accel-Buffering", "no"),
        ]
        return request.make_response(generator, headers=headers)
