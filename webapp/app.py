"""aROMa web app: a fast, read-only window on the game. Run with `python -m webapp` (see webapp/__main__.py)."""
import os
import re

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from database import Base, Database
from webapp import auth, data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
IMAGE_DIR = os.path.join(BASE_DIR, 'images')
THUMB_DIR = os.path.join(BASE_DIR, 'cache', 'thumbs')
GUILD_ART_DIR = os.path.join(BASE_DIR, 'assets', 'guild')
BADGE_DIR = os.path.join(BASE_DIR, 'assets', 'badges')
THUMB_WIDTHS = (128, 256, 512)
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')

app = FastAPI(title="aROMa", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.on_event("startup")
def create_tables():
    import models.webapp  # noqa: F401  (registers the table)
    Base.metadata.create_all(bind=Database().engine, tables=[models.webapp.WebLoginToken.__table__])


def current_user(aroma_session: str = Cookie(default=None)):
    user_id = auth.read_session(aroma_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="login required")
    return user_id


def same_site_request(x_requested_with: str = Header(default=None)):
    """State-changing calls must come from this app's own script: a plain cross-site form cannot set the header."""
    if x_requested_with != "aroma":
        raise HTTPException(status_code=403, detail="bad request origin")


@app.get("/login")
def login(token: str, response: Response):
    user_id = auth.consume_token(token)
    if not user_id:
        return RedirectResponse("/?login=expired")
    redirect = RedirectResponse("/#/profilo", status_code=303)
    redirect.set_cookie(auth.COOKIE, auth.make_session(user_id), max_age=auth.SESSION_MAX_AGE, httponly=True,
                        samesite="lax", secure=auth.webapp_url().startswith("https"))
    return redirect


@app.post("/api/logout", dependencies=[Depends(same_site_request)])
def logout(response: Response):
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}


# --- public: the catalogue is the same for everyone, so it is sent once and searched in the browser ---

@app.get("/api/characters")
def characters(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    return data.catalog()


@app.get("/api/characters/{char_id}")
def character(char_id: int, response: Response):
    detail = data.character_detail(char_id)
    if not detail:
        raise HTTPException(status_code=404, detail="character not found")
    response.headers["Cache-Control"] = "public, max-age=300"
    return detail


@app.get("/api/me")
def me(user_id: int = Depends(current_user)):
    profile = data.profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="user not found")
    return profile


class NpubBody(BaseModel):
    npub: str


class CodeBody(BaseModel):
    code: str


@app.get("/api/me/nostr")
def nostr_state(user_id: int = Depends(current_user)):
    return data.nostr_status(user_id)


@app.post("/api/me/nostr/start", dependencies=[Depends(same_site_request)])
def nostr_start(body: NpubBody, user_id: int = Depends(current_user)):
    from services import nostr_service
    ok, message = nostr_service.start_link(user_id, body.npub)
    return {"ok": ok, "message": message}


@app.post("/api/me/nostr/confirm", dependencies=[Depends(same_site_request)])
def nostr_confirm(body: CodeBody, user_id: int = Depends(current_user)):
    from services import nostr_service
    ok, message = nostr_service.confirm_link(user_id, body.code)
    return {"ok": ok, "message": message, **data.nostr_status(user_id)}


@app.post("/api/me/nostr/unlink", dependencies=[Depends(same_site_request)])
def nostr_unlink(user_id: int = Depends(current_user)):
    from services import nostr_service
    return {"ok": nostr_service.unlink(user_id), **data.nostr_status(user_id)}


@app.get("/api/me/characters")
def me_characters(user_id: int = Depends(current_user)):
    return data.my_characters(user_id) or {}


@app.get("/api/me/stats")
def me_stats(user_id: int = Depends(current_user)):
    return data.stats(user_id)


@app.get("/api/me/achievements")
def me_achievements(user_id: int = Depends(current_user)):
    return data.achievements(user_id)


class ItemBody(BaseModel):
    id: int


class AllocBody(BaseModel):
    stat: str
    count: int = 1


class BuildBody(BaseModel):
    allocations: dict[str, int] | None = None
    preset: str | None = None


class TitleBody(BaseModel):
    title: str | None = None


class NameBody(BaseModel):
    name: str


class DragonBody(BaseModel):
    dragon: str
    choices: list[str]


class CharBody(BaseModel):
    id: int
    buy: bool = False


class UpgradeBody(BaseModel):
    id: int
    count: int = 1


class TransformBody(BaseModel):
    action: str
    id: int | None = None


class SellBody(BaseModel):
    item: str
    quantity: int
    price: int
    days: int = 7


class DungeonBody(BaseModel):
    id: int


class GuildBody(BaseModel):
    action: str
    option: str | None = None
    slot: int | None = None
    amount: int | None = None
    guild_id: int | None = None
    building: str | None = None


@app.get("/api/me/equipment")
def me_equipment(user_id: int = Depends(current_user)):
    return data.equipment(user_id)


@app.post("/api/me/equipment/equip", dependencies=[Depends(same_site_request)])
def equip(body: ItemBody, user_id: int = Depends(current_user)):
    return data.equip(user_id, body.id, True)


@app.post("/api/me/equipment/unequip", dependencies=[Depends(same_site_request)])
def unequip(body: ItemBody, user_id: int = Depends(current_user)):
    return data.equip(user_id, body.id, False)


@app.get("/api/me/guild")
def me_guild(user_id: int = Depends(current_user)):
    return data.guild(user_id)


@app.post("/api/me/guild", dependencies=[Depends(same_site_request)])
def guild_move(body: GuildBody, user_id: int = Depends(current_user)):
    return data.guild_action(user_id, body.action, body.amount, body.guild_id, body.building, body.option, body.slot)


@app.post("/api/me/stats/allocate", dependencies=[Depends(same_site_request)])
def allocate(body: AllocBody, user_id: int = Depends(current_user)):
    return data.allocate(user_id, body.stat, body.count)


@app.post("/api/me/stats/build", dependencies=[Depends(same_site_request)])
def build(body: BuildBody, user_id: int = Depends(current_user)):
    return data.set_build(user_id, body.allocations, body.preset)


@app.post("/api/me/title", dependencies=[Depends(same_site_request)])
def title(body: TitleBody, user_id: int = Depends(current_user)):
    return data.set_title(user_id, body.title)


@app.get("/api/me/inventory")
def me_inventory(user_id: int = Depends(current_user)):
    return data.inventory(user_id)


@app.post("/api/me/inventory/use", dependencies=[Depends(same_site_request)])
def inventory_use(body: NameBody, user_id: int = Depends(current_user)):
    return data.use_item(user_id, body.name)


@app.post("/api/me/inventory/upgrade", dependencies=[Depends(same_site_request)])
def inventory_upgrade(body: UpgradeBody, user_id: int = Depends(current_user)):
    return data.upgrade_material(user_id, body.id, body.count)


@app.post("/api/me/dragon", dependencies=[Depends(same_site_request)])
def me_dragon(body: DragonBody, user_id: int = Depends(current_user)):
    return data.summon_dragon(user_id, body.dragon, body.choices)


@app.post("/api/me/character", dependencies=[Depends(same_site_request)])
def pick_character(body: CharBody, user_id: int = Depends(current_user)):
    return data.pick_character(user_id, body.id, body.buy)


@app.get("/api/me/transformations")
def me_transformations(user_id: int = Depends(current_user)):
    return data.transformations(user_id)


@app.post("/api/me/transformations", dependencies=[Depends(same_site_request)])
def me_transform(body: TransformBody, user_id: int = Depends(current_user)):
    return data.transform(user_id, body.action, body.id)


@app.post("/api/dungeons/start", dependencies=[Depends(same_site_request)])
def dungeon_start(body: DungeonBody, user_id: int = Depends(current_user)):
    return data.start_solo_dungeon(user_id, body.id)


@app.get("/api/market")
def market_search(q: str = "", page: int = 1, user_id: int = Depends(current_user)):
    return data.market(user_id, q, page)


@app.post("/api/market/sell", dependencies=[Depends(same_site_request)])
def market_sell(body: SellBody, user_id: int = Depends(current_user)):
    return data.market_sell(user_id, body.item, body.quantity, body.price, body.days)


@app.get("/api/guides")
def guide_list(user_id: int = Depends(current_user)):
    return data.guides()


@app.get("/api/guides/{name}")
def guide_page(name: str, user_id: int = Depends(current_user)):
    found = data.guide(name)
    if not found:
        raise HTTPException(404, "Guida non trovata")
    return found


@app.get("/api/season")
def season(user_id: int = Depends(current_user)):
    return data.season(user_id)


@app.get("/api/dungeons")
def dungeons(user_id: int = Depends(current_user)):
    return data.dungeons(user_id)


@app.get("/api/games")
def games_search(q: str = "", platform: str = None, genre: str = None, language: str = None, region: str = None,
                 sort: str = "titolo", page: int = 1, per_page: int = 48,
                 user_id: int = Depends(current_user)):
    from webapp import games
    result = games.search(q[:100], platform, genre, language, region, sort, page, per_page)
    result['bot'] = os.getenv('BOT_USERNAME', '').lstrip('@')  # lets each card open the game in the bot
    return result


@app.get("/api/games/{game_id}")
def game(game_id: int, user_id: int = Depends(current_user)):
    from webapp import games
    found = games.detail(game_id)
    if not found:
        raise HTTPException(404, "Gioco non trovato")
    return found


GAME_COVERS = os.path.join(BASE_DIR, "cache", "game_covers")


@app.get("/img/game/{game_id}.webp")
def game_cover(game_id: int, user_id: int = Depends(current_user)):
    path = os.path.join(GAME_COVERS, f"{int(game_id)}.webp")
    if not os.path.isfile(path):
        raise HTTPException(404, "Nessuna copertina")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/health")
def health():
    return {"ok": True}


# --- pictures: whatever the bot has, scaled down once and cached on disk ---

def _find_image(name, folder=None):
    for ext in IMAGE_EXTENSIONS:
        path = os.path.join(folder or IMAGE_DIR, name + ext)
        if os.path.isfile(path):
            return path
    return os.path.join(folder, 'missing') if folder else os.path.join(IMAGE_DIR, 'default.png')


def make_thumbnail(name, width, folder=None):
    """Path of the WebP for this picture and width, made (and cached on disk) the first time; None if there is no picture."""
    source = _find_image(name, folder)
    if not os.path.isfile(source):
        return None
    thumb = os.path.join(THUMB_DIR, f"{'guild_' if folder else ''}{os.path.basename(source)}.{width}.webp")
    if not os.path.isfile(thumb) or os.path.getmtime(thumb) < os.path.getmtime(source):
        from PIL import Image
        os.makedirs(THUMB_DIR, exist_ok=True)
        with Image.open(source) as img:
            img = img.convert("RGBA") if img.mode in ("P", "LA") else img.convert("RGB")
            img.thumbnail((width, width * 2))
            img.save(thumb, "WEBP", quality=82)
    return thumb


@app.get("/img/{name}/{width}.webp")
def image(name: str, width: int):
    if not re.fullmatch(r"[\w()'&.\- ]+", name) or width not in THUMB_WIDTHS:
        raise HTTPException(status_code=404)
    try:
        thumb = make_thumbnail(name, width)
    except Exception as e:
        print(f"[WEB] thumbnail failed for {name}: {e}")
        thumb = None
    if not thumb:
        raise HTTPException(status_code=404)
    return FileResponse(thumb, media_type="image/webp", headers={"Cache-Control": "public, max-age=604800"})


@app.get("/img/guild/{name}/{width}.webp")
def guild_image(name: str, width: int):
    if not re.fullmatch(r"[a-z]+", name) or width not in THUMB_WIDTHS:
        raise HTTPException(status_code=404)
    thumb = make_thumbnail(name, width, GUILD_ART_DIR)
    if not thumb:
        raise HTTPException(status_code=404)
    return FileResponse(thumb, media_type="image/webp", headers={"Cache-Control": "public, max-age=604800"})


@app.get("/badges/{name}")
def badge(name: str):
    """Badge pictures, public: this is the address the Nostr badge definitions point at."""
    if not re.fullmatch(r"[\w\-]+\.png", name):
        raise HTTPException(status_code=404)
    path = os.path.join(BADGE_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=2592000, immutable"})


@app.get("/p/{char_id}")
def share_character(char_id: int):
    """A link that previews well when pasted into a chat, then opens the character in the app."""
    c = data.character_detail(char_id)
    if not c:
        raise HTTPException(status_code=404)
    base = auth.webapp_url()
    title = f"{c['name']} · Lv. {c['level']} · aROMa"
    desc = f"{c['attack']['name']}: {c['attack']['damage']} danni. {c['description']}"
    from html import escape
    page = (f'<!doctype html><html lang="it"><head><meta charset="utf-8"><title>{escape(title)}</title>'
            f'<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(desc)}">'
            f'<meta property="og:image" content="{base}/img/{escape(c["img"])}/512.webp"><meta name="twitter:card" content="summary_large_image">'
            f'<meta http-equiv="refresh" content="0; url=/#/personaggio/{c["id"]}"></head><body>'
            f'<a href="/#/personaggio/{c["id"]}">{escape(title)}</a></body></html>')
    return HTMLResponse(page, headers={"Cache-Control": "public, max-age=300"})


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'), headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
