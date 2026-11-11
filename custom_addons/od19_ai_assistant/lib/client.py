# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Minimal OpenAI-compatible chat client.

Works with any endpoint exposing the OpenAI ``/chat/completions`` API, e.g.

* Ollama      -> http://localhost:11434/v1            (free, 100% local)
* Groq        -> https://api.groq.com/openai/v1       (free tier)
* Google      -> https://generativelanguage.googleapis.com/v1beta/openai
* OpenRouter  -> https://openrouter.ai/api/v1         (free models)
* Mistral     -> https://api.mistral.ai/v1

No vendor SDK is required: only ``requests`` which ships with Odoo.
"""

import json
import logging

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


class AiClientError(Exception):
    """Raised when the AI endpoint cannot be reached or returns an error."""


def chat_completion(base_url, model, messages, api_key=None, timeout=DEFAULT_TIMEOUT):
    """Return the assistant message content for the given ``messages`` list.

    :param str base_url: root URL of the OpenAI-compatible endpoint
        (e.g. ``http://localhost:11434/v1``)
    :param str model: model name (e.g. ``qwen2.5:7b``)
    :param list messages: list of ``{"role": ..., "content": ...}`` dicts
    :param str api_key: optional bearer token
    :param int timeout: request timeout in seconds
    """
    if not base_url:
        raise AiClientError("AI base URL is not configured.")
    if not model:
        raise AiClientError("AI model name is not configured.")

    url = "%s/chat/completions" % base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    payload = {"model": model, "messages": messages, "stream": False}

    _logger.debug("AI request -> %s (%s)", url, model)
    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=timeout
        )
    except requests.exceptions.RequestException as exc:
        raise AiClientError("Cannot reach AI endpoint %s: %s" % (url, exc)) from exc

    if response.status_code >= 400:
        raise AiClientError(
            "AI endpoint returned HTTP %s: %s"
            % (response.status_code, response.text[:500])
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        raise AiClientError(
            "Unexpected AI response: %s" % response.text[:500]
        ) from exc


def chat_completion_stream(
    base_url, model, messages, api_key=None, timeout=DEFAULT_TIMEOUT
):
    """Yield assistant content fragments as they are produced (SSE).

    Works against any OpenAI-compatible ``/chat/completions`` endpoint that
    supports ``stream=true`` (Ollama does). Each yielded value is a ``str``
    fragment of the answer, so the caller can forward it to the browser
    immediately instead of waiting for the full completion.
    """
    if not base_url:
        raise AiClientError("AI base URL is not configured.")
    if not model:
        raise AiClientError("AI model name is not configured.")

    url = "%s/chat/completions" % base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    payload = {"model": model, "messages": messages, "stream": True}

    _logger.debug("AI stream -> %s (%s)", url, model)
    try:
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout,
            stream=True,
        )
    except requests.exceptions.RequestException as exc:
        raise AiClientError("Cannot reach AI endpoint %s: %s" % (url, exc)) from exc

    with response:
        if response.status_code >= 400:
            raise AiClientError(
                "AI endpoint returned HTTP %s: %s"
                % (response.status_code, response.text[:500])
            )
        for raw_line in response.iter_lines(decode_unicode=False):
            if not raw_line:
                continue
            # Ollama replies with ``Content-Type: text/event-stream`` and no
            # charset, so ``requests`` would decode the body as ISO-8859-1 and
            # garble Thai text. Decode UTF-8 explicitly instead of trusting
            # ``response.encoding``.
            line = raw_line.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                yield content
