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

from ..lib.client import AiClientError, chat_completion_stream
from ..models.od19_ai_chat import MAX_TOOL_ROUNDS

_logger = logging.getLogger(__name__)


def _sse(payload):
    """Format ``payload`` as a single server-sent event."""
    return "data: %s\n\n" % json.dumps(payload, ensure_ascii=False)


def _stream_answer(registry, uid, context, chat_id, question):
    """Generator yielding SSE events for one assistant answer."""
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, uid, context)
        chat = None
        try:
            chat = env["od19.ai.chat"].browse(chat_id)
            if not chat.exists() or chat.user_id.id != uid:
                yield _sse({"type": "error", "message": "ไม่พบบทสนทนานี้"})
                return
            if not question:
                yield _sse({"type": "error", "message": "กรุณากรอกคำถามก่อน"})
                return

            config = chat._get_ai_config()
            system_prompt = chat._build_system_prompt(config["system_prompt"])
            tool_model = env["od19.ai.tool"]
            chat.write({"state": "draft", "prompt": False})
            chat._post_message("user", question)

            answer = None
            for _round in range(MAX_TOOL_ROUNDS):
                buffer = []
                for token in chat_completion_stream(
                    config["base_url"],
                    config["model"],
                    chat._build_messages(system_prompt),
                    api_key=config["api_key"],
                    timeout=config["timeout"],
                ):
                    buffer.append(token)
                    yield _sse({"type": "delta", "content": token})

                raw = "".join(buffer)
                call = chat._parse_tool_call(raw)
                if not call:
                    answer = raw
                    yield _sse({"type": "round_end", "kind": "answer"})
                    break

                # The streamed text was a tool request, not an answer:
                # tell the browser to drop it and show a tool chip instead.
                yield _sse({"type": "round_end", "kind": "tool"})
                name, arguments = call
                chat._post_message("assistant", raw)
                yield _sse({"type": "tool", "name": name, "status": "running"})
                chat._post_message("tool", tool_model.execute(name, arguments))
                yield _sse({"type": "tool", "name": name, "status": "done"})
            else:
                answer = (
                    "ขออภัย ระบบเรียกใช้เครื่องมือหลายรอบเกินไป "
                    "กรุณาตั้งคำถามให้เฉพาะเจาะจงมากขึ้น"
                )
                yield _sse({"type": "round_end", "kind": "answer"})
                yield _sse({"type": "delta", "content": answer})

            chat._post_message("assistant", answer)
            chat.write({"state": "done", "model_used": config["model"]})
            yield _sse(
                {"type": "done", "chat_id": chat.id, "model": config["model"]}
            )
        except AiClientError as exc:
            if chat:
                chat._post_message("system", "เกิดข้อผิดพลาด: %s" % exc)
                chat.write({"state": "error"})
            yield _sse({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001 - keep the stream alive
            _logger.exception("OD19 AI stream failed")
            if chat:
                try:
                    chat._post_message("system", "เกิดข้อผิดพลาด: %s" % exc)
                    chat.write({"state": "error"})
                except Exception:  # noqa: BLE001
                    pass
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
        )
        headers = [
            ("Content-Type", "text/event-stream; charset=utf-8"),
            ("Cache-Control", "no-cache"),
            # Ask Nginx to forward each event immediately instead of buffering.
            ("X-Accel-Buffering", "no"),
        ]
        return request.make_response(generator, headers=headers)
