"""Login for the web app: the bot hands out a one-time link, the browser trades it for a signed cookie."""
import hashlib
import hmac
import os
import urllib.request
import time
import json
from urllib.parse import parse_qsl, urlparse
import secrets
from datetime import datetime, timedelta

from itsdangerous import BadSignature, URLSafeTimedSerializer

from database import Database
from models.webapp import WebLoginToken

TOKEN_TTL = timedelta(minutes=10)
SESSION_MAX_AGE = 7 * 24 * 3600
COOKIE = "aroma_session"

_secret = os.getenv("WEBAPP_SECRET")
if not _secret:
    # Without a configured secret sessions die with the process: fine for development only
    _secret = secrets.token_hex(32)
    print("[WEB] WEBAPP_SECRET is not set: sessions will not survive a restart")
_serializer = URLSafeTimedSerializer(_secret, salt="aroma-web-session")


LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
NGROK_API = os.getenv("NGROK_API", "http://ngrok:4040/api/tunnels")
QUICKTUNNEL_API = os.getenv("QUICKTUNNEL_API", "http://quicktunnel:2000/quicktunnel")  # cloudflared quick tunnel
_ngrok_cache = {"at": 0.0, "url": None}


def _public(url):
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and bool(parsed.hostname) and parsed.hostname.lower() not in LOCAL_HOSTS


def _ngrok_url():
    """The address a tunnel (ngrok, or a Cloudflare quick tunnel) gave the web app. Free ones change whenever the
    tunnel restarts, so it is asked again every half minute instead of being written down."""
    if time.time() - _ngrok_cache["at"] < 30:
        return _ngrok_cache["url"]
    url = None
    try:
        with urllib.request.urlopen(NGROK_API, timeout=2) as r:
            tunnels = json.load(r).get("tunnels", [])
        url = next((t["public_url"] for t in tunnels if t.get("public_url", "").startswith("https://")), None)
    except Exception:
        pass
    if not url:
        try:
            with urllib.request.urlopen(QUICKTUNNEL_API, timeout=2) as r:
                host = json.load(r).get("hostname")
            url = f"https://{host}" if host else None
        except Exception:
            pass  # no tunnel running: webapp_url() then says so
    _ngrok_cache.update(at=time.time(), url=url)
    return url


def webapp_url():
    """The public address of the web app: WEBAPP_URL, or else the ngrok tunnel's. There is deliberately no localhost
    default: such a link works only on the machine that sends it, so without a real address no link is made."""
    url = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
    if not _public(url):
        url = (_ngrok_url() or "").rstrip("/")
    if not _public(url):
        raise RuntimeError("no public address for the web app: set WEBAPP_URL, or start a tunnel (COMPOSE_PROFILES=ngrok or quicktunnel)")
    return url


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_login_link(user_id):
    """A link the user opens once, within ten minutes. Older unused links stop working."""
    token = secrets.token_urlsafe(32)
    session = Database().get_session()
    try:
        session.query(WebLoginToken).filter(
            WebLoginToken.user_id == user_id, WebLoginToken.used_at == None).delete()
        session.add(WebLoginToken(token_hash=_hash(token), user_id=user_id,
                                  expires_at=datetime.now() + TOKEN_TTL))
        session.commit()
    finally:
        session.close()
    return f"{webapp_url()}/login?token={token}"


def consume_token(token):
    """The user id the token belongs to, or None if unknown, expired or already used."""
    session = Database().get_session()
    try:
        row = session.query(WebLoginToken).filter_by(token_hash=_hash(token)).first()
        if not row or row.used_at or row.expires_at < datetime.now():
            return None
        row.used_at = datetime.now()
        session.commit()
        return row.user_id
    finally:
        session.close()


def make_session(user_id):
    return _serializer.dumps({"uid": int(user_id)})


def read_session(cookie):
    if not cookie:
        return None
    try:
        return _serializer.loads(cookie, max_age=SESSION_MAX_AGE)["uid"]
    except (BadSignature, KeyError):
        return None


INIT_DATA_MAX_AGE = 24 * 3600


def telegram_user(init_data, bot_token=None, now=None):
    """The Telegram id inside a Mini App's initData, or None unless Telegram signed it for this bot, recently."""
    if bot_token is None:
        from settings import BOT_TOKEN as bot_token
    try:
        fields = dict(parse_qsl(init_data or "", keep_blank_values=True, strict_parsing=True))
        signature = fields.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        if (now or time.time()) - int(fields["auth_date"]) > INIT_DATA_MAX_AGE:
            return None
        return int(json.loads(fields["user"])["id"])
    except (KeyError, ValueError, TypeError):
        return None
