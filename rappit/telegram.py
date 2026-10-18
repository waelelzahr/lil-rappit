"""Minimal Telegram Bot API client for the review loop."""
import json
import os
from pathlib import Path

import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _call(method: str, files=None, **params):
    url = API.format(token=os.environ["TELEGRAM_BOT_TOKEN"], method=method)
    data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()}
    r = requests.post(url, data=data, files=files, timeout=120)
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {body}")
    return body["result"]


def chat_id():
    return os.environ["TELEGRAM_CHAT_ID"]


def buttons(item_id: str):
    return {"inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": f"approve:{item_id}"},
        {"text": "🔁 Redo", "callback_data": f"redo:{item_id}"},
    ]]}


def send_item(item_id: str, kind: str, path: Path, caption: str) -> int:
    """Send a draft with Approve/Redo buttons. Returns the message id."""
    with open(path, "rb") as f:
        if kind == "reel":
            res = _call("sendVideo", files={"video": f}, chat_id=chat_id(),
                        caption=caption[:1024], supports_streaming=True,
                        reply_markup=buttons(item_id))
        else:
            res = _call("sendPhoto", files={"photo": f}, chat_id=chat_id(),
                        caption=caption[:1024], reply_markup=buttons(item_id))
    return res["message_id"]


def send_text(text: str, reply_to: int | None = None):
    params = {"chat_id": chat_id(), "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    return _call("sendMessage", **params)


def updates(offset: int):
    return _call("getUpdates", offset=offset, timeout=0,
                 allowed_updates=["message", "callback_query"])


def answer(callback_id: str, text: str):
    try:
        _call("answerCallbackQuery", callback_query_id=callback_id, text=text)
    except RuntimeError:
        pass  # old callbacks expire; harmless


def clear_buttons(message_id: int):
    try:
        _call("editMessageReplyMarkup", chat_id=chat_id(), message_id=message_id,
              reply_markup={"inline_keyboard": []})
    except RuntimeError:
        pass
