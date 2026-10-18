"""Email review channel (Gmail SMTP + IMAP with an app password).

Drafts are emailed with subject "[Rappit:<item_id>] ...". You approve by replying
"OK", regenerate by replying "REDO", or reply with any other text to regenerate
using that text as a note.
"""
import email
import email.header
import imaplib
import os
import re
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from pathlib import Path

SMTP_HOST, IMAP_HOST = "smtp.gmail.com", "imap.gmail.com"
TAG_RE = re.compile(r"\[Rappit:([\w\-]+)\]")
APPROVE_WORDS = {"ok", "okay", "approve", "approved", "yes", "y", "go", "post", "👍", "✅", "good"}


def _addr():
    return os.environ["EMAIL_ADDRESS"]


def _to():
    return os.environ.get("EMAIL_TO") or _addr()


def _send(msg: EmailMessage):
    msg["From"] = f"Rappit Studio <{_addr()}>"
    msg["To"] = _to()
    with smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=120) as s:
        s.login(_addr(), os.environ["EMAIL_APP_PASSWORD"])
        s.send_message(msg)


def send_item(item_id: str, kind: str, path: Path, caption: str, title: str = "",
              version: int = 1) -> str:
    msg = EmailMessage()
    label = {"reel": "Reel", "mugshot": "Mugshot photo", "soft": "Soft-side photo"}[kind]
    v = f" v{version}" if version > 1 else ""
    msg["Subject"] = f"[Rappit:{item_id}] {label}{v}" + (f" · {title}" if title else "")
    msg["Message-ID"] = make_msgid(domain="rappit.local")
    msg["X-Rappit-Draft"] = item_id
    msg.set_content(
        f"{caption}\n\n"
        "———\n"
        "Reply OK to approve.\n"
        "Reply REDO to regenerate.\n"
        "Or reply with what to change (e.g. \"make the detective a crocodile\").\n"
    )
    data = path.read_bytes()
    if path.suffix == ".mp4":
        maintype, subtype = "video", "mp4"
    else:
        maintype, subtype = "image", ("png" if data[:4] == b"\x89PNG" else "jpeg")
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)
    _send(msg)
    return msg["Message-ID"]


def send_text(text: str, subject: str = "[Rappit] Update"):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["X-Rappit-Draft"] = "info"
    msg.set_content(text)
    _send(msg)


def _body_text(m) -> str:
    part = None
    if m.is_multipart():
        for p in m.walk():
            if p.get_content_type() == "text/plain" and not p.get("Content-Disposition"):
                part = p
                break
    else:
        part = m
    if part is None:
        return ""
    raw = part.get_payload(decode=True) or b""
    text = raw.decode(part.get_content_charset() or "utf-8", errors="replace")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">") or re.match(r"^On .+wrote:$", s) or s.startswith("———"):
            break
        if re.match(r"^(Le|El|Am) .+(écrit|escribió|schrieb).*:$", s):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def classify(text: str) -> tuple[str, str | None]:
    """-> ('approve', None) | ('redo', note or None)"""
    t = text.strip()
    first = t.split()[0].lower().strip(".!,:") if t else ""
    if first in APPROVE_WORDS and len(t.split()) <= 3:
        return "approve", None
    if first == "redo" and len(t.split()) == 1:
        return "redo", None
    if first == "redo":
        return "redo", t[4:].strip(" :-") or None
    return "redo", t or None


def fetch_replies(seen_ids: set[str]) -> list[dict]:
    """Return new replies: [{msgid, item_id, action, note}] from the owner only."""
    out = []
    owners = {_addr().lower(), _to().lower()}
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        M.login(_addr(), os.environ["EMAIL_APP_PASSWORD"])
        M.select('"[Gmail]/All Mail"', readonly=True)
        typ, data = M.search(None, 'X-GM-RAW', '"subject:Rappit newer_than:14d"')
        for num in (data[0].split() if data and data[0] else []):
            typ, msg_data = M.fetch(num, "(BODY.PEEK[])")
            m = email.message_from_bytes(msg_data[0][1])
            mid = (m.get("Message-ID") or "").strip()
            if not mid or mid in seen_ids or m.get("X-Rappit-Draft"):
                continue
            subj = str(email.header.make_header(email.header.decode_header(m.get("Subject", ""))))
            tag = TAG_RE.search(subj)
            sender = parseaddr(m.get("From", ""))[1].lower()
            if not tag or sender not in owners or not subj.lower().lstrip().startswith(("re:", "aw:", "rép", "tr:")):
                continue
            action, note = classify(_body_text(m))
            out.append({"msgid": mid, "item_id": tag.group(1), "action": action, "note": note})
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return out
