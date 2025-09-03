from __future__ import annotations
import hashlib
from fastapi import Header, HTTPException, Request, Response
from ..common.config import SETTINGS
from ..db.session import get_session
from ..db.models import APIKey

def require_invite(request: Request):
    if not SETTINGS.INVITE_TOKEN:
        return
    header = request.headers.get("X-Invite-Token", "")
    cookie = request.cookies.get("invite", "")
    if header == SETTINGS.INVITE_TOKEN or cookie == SETTINGS.INVITE_TOKEN:
        return
    raise HTTPException(status_code=403, detail="Invite required")

def set_invite_cookie(token: str, response: Response):
    if SETTINGS.INVITE_TOKEN and token == SETTINGS.INVITE_TOKEN:
        response.set_cookie(
            key="invite",
            value=token,
            httponly=True,
            samesite="Lax",
            domain=SETTINGS.COOKIE_DOMAIN or None,
            secure=False,  # switch True when behind HTTPS + domain
            max_age=60 * 60 * 8,
        )
        return {"ok": True}
    raise HTTPException(status_code=403, detail="Bad invite token")

def require_api_key(x_api_key: str = Header(default="")):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    digest = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    s = get_session()
    row = s.query(APIKey).filter(APIKey.key_hash == digest, APIKey.active.is_(True)).first()
    if not row:
        raise HTTPException(status_code=403, detail="Invalid API key")
