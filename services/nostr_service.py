"""Nostr badges (NIP-58) for achievements, and the npub <-> Telegram account link."""
import asyncio
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta

from database import Database
from models.achievements import Achievement, UserAchievement
from models.nostr import NostrBadgeOutbox, NostrLinkChallenge
from models.user import Utente

TIER_ORDER = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'legendary']
DEFAULT_RELAYS = "wss://relay.damus.io,wss://nos.lol,wss://relay.primal.net"
CHALLENGE_TTL = timedelta(minutes=15)
CHALLENGE_COOLDOWN = timedelta(seconds=60)
MAX_CODE_ATTEMPTS = 5
MAX_SEND_ATTEMPTS = 8
BADGE_KIND = 30009
AWARD_KIND = 8


def _sdk():
    # Imported lazily: the bot must start even where nostr-sdk is not installed.
    import nostr_sdk
    return nostr_sdk


def is_configured():
    return bool(os.getenv("NOSTR_NSEC"))


def _relays():
    return [r.strip() for r in os.getenv("NOSTR_RELAYS", DEFAULT_RELAYS).split(",") if r.strip()]


def _keys():
    n = _sdk()
    return n.Keys(n.SecretKey.parse(os.environ["NOSTR_NSEC"]))


def badge_image_name(achievement_key, tier):
    # Season podiums are created per season: they all share three images.
    podium = re.fullmatch(r'season_\d+_podium_(\d)', achievement_key)
    return f"season-podium-{podium.group(1)}" if podium else f"{achievement_key}-{tier}"


def badge_id(achievement_key, tier):
    return f"{achievement_key}-{tier}"


def build_badge_definition(keys, achievement_key, tier, name, description):
    n = _sdk()
    tags = [
        n.Tag.identifier(badge_id(achievement_key, tier)),
        n.Tag.custom("name", [f"{name} ({tier.capitalize()})"]),
        n.Tag.custom("description", [description or name]),
    ]
    image_base = os.getenv("NOSTR_BADGE_IMAGE_BASE", "").rstrip("/")
    if not image_base:
        try:
            from webapp.auth import webapp_url
            url = webapp_url()
            if url.startswith("https://"):
                image_base = url + "/badges"  # the web app serves them
        except Exception:
            pass  # no public address: badges go out without a picture
    if image_base:
        tags.append(n.Tag.custom("image", [f"{image_base}/{badge_image_name(achievement_key, tier)}.png"]))
    return n.EventBuilder(n.Kind(BADGE_KIND), "").tags(tags).finalize(keys)


def build_badge_award(keys, achievement_key, tier, recipient):
    n = _sdk()
    coordinate = n.Coordinate(n.Kind(BADGE_KIND), keys.public_key(), badge_id(achievement_key, tier))
    tags = [n.Tag.coordinate(coordinate), n.Tag.public_key(recipient)]
    return n.EventBuilder(n.Kind(AWARD_KIND), "").tags(tags).finalize(keys)


async def _publish(events):
    """Send events to every relay; returns the ids of those at least one relay accepted."""
    n = _sdk()
    client = n.Client()
    for url in _relays():
        await client.add_relay(n.RelayUrl.parse(url))
    await client.connect()
    accepted = set()
    try:
        for event in events:
            output = await client.send_event(event)
            if output.success:
                accepted.add(event.id().to_hex())
    finally:
        await client.shutdown()
    return accepted


def _parse_npub(value):
    n = _sdk()
    try:
        return n.PublicKey.parse(value.strip())
    except Exception:
        return None


def queue_badge(user_id, achievement_key, tier, session=None):
    """Queue one badge for a user who linked an npub; a no-op for everyone else."""
    local = session is None
    db = Database()
    session = session or db.get_session()
    try:
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.npub:
            return False
        exists = session.query(NostrBadgeOutbox).filter_by(
            user_id=user_id, achievement_key=achievement_key, tier=tier, npub=user.npub).first()
        if exists:
            return False
        session.add(NostrBadgeOutbox(
            user_id=user_id, achievement_key=achievement_key, tier=tier, npub=user.npub))
        if local:
            session.commit()
        else:
            session.flush()
        return True
    except Exception:
        if local:
            session.rollback()
        raise
    finally:
        if local:
            session.close()


def queue_unlocked_badges(user_id, session):
    """Queue every tier already earned (bronze up to the current one). Returns how many were new."""
    queued = 0
    owned = session.query(UserAchievement).filter(
        UserAchievement.user_id == user_id, UserAchievement.current_tier != None).all()
    for ua in owned:
        achievement = session.query(Achievement).filter_by(achievement_key=ua.achievement_key).first()
        if not achievement:
            continue
        try:
            tiers = json.loads(achievement.tiers)
        except ValueError:
            tiers = {}
        if ua.current_tier not in TIER_ORDER:
            continue
        reached = TIER_ORDER[:TIER_ORDER.index(ua.current_tier) + 1]
        for tier in reached:
            if tier in tiers and queue_badge(user_id, ua.achievement_key, tier, session=session):
                queued += 1
    return queued


def reconcile_all():
    """Queue whatever a linked user has unlocked but not been queued for. Returns how many."""
    session = Database().get_session()
    try:
        total = 0
        for (user_id,) in session.query(Utente.id_telegram).filter(Utente.npub != None).all():
            total += queue_unlocked_badges(user_id, session)
        session.commit()
        return total
    except Exception as e:
        session.rollback()
        print(f"[Nostr] reconcile_all failed: {e}")
        return 0
    finally:
        session.close()


def start_link(user_id, npub):
    """DM a one-time code to the npub. Returns (ok, message)."""
    if not is_configured():
        return False, "I badge Nostr non sono ancora attivi su questo bot."
    pubkey = _parse_npub(npub)
    if pubkey is None or not npub.strip().startswith("npub1"):
        return False, "Quella non sembra una npub valida (inizia con `npub1…`)."
    npub = pubkey.to_bech32()

    session = Database().get_session()
    try:
        taken = session.query(Utente).filter(Utente.npub == npub, Utente.id_telegram != user_id).first()
        if taken:
            return False, "Questa npub è già collegata a un altro account."

        challenge = session.query(NostrLinkChallenge).filter_by(user_id=user_id).first()
        if challenge and datetime.now() - challenge.created_at < CHALLENGE_COOLDOWN:
            return False, "Aspetta un minuto prima di chiedere un nuovo codice."

        code = secrets.token_hex(3).upper()
        n = _sdk()
        keys = _keys()

        async def send():
            gift = await n.nip17_make_private_msg_async(
                keys, pubkey,
                f"aROMa: il tuo codice di collegamento è {code}. Scrivilo al bot su Telegram con /nostr codice {code}",
            )
            return await _publish([gift])

        if not asyncio.run(send()):
            return False, "Non sono riuscito a inviare il messaggio ai relay Nostr. Riprova tra poco."

        if challenge:
            challenge.npub, challenge.code, challenge.attempts = npub, code, 0
            challenge.created_at = datetime.now()
        else:
            session.add(NostrLinkChallenge(user_id=user_id, npub=npub, code=code))
        session.commit()
        return True, ("📨 Ti ho mandato un messaggio privato Nostr con un codice.\n"
                      "Aprilo nel tuo client Nostr e scrivi qui `/nostr codice XXXXXX`. Vale 15 minuti.")
    except Exception as e:
        session.rollback()
        print(f"[Nostr] start_link failed: {e}")
        return False, "Errore durante il collegamento, riprova più tardi."
    finally:
        session.close()


def confirm_link(user_id, code):
    """Check the code and bind the npub. Returns (ok, message)."""
    session = Database().get_session()
    try:
        challenge = session.query(NostrLinkChallenge).filter_by(user_id=user_id).first()
        if not challenge:
            return False, "Nessun collegamento in corso. Usa `/nostr npub1…`."
        if datetime.now() - challenge.created_at > CHALLENGE_TTL:
            session.delete(challenge)
            session.commit()
            return False, "Il codice è scaduto. Richiedine uno nuovo con `/nostr npub1…`."
        if challenge.attempts >= MAX_CODE_ATTEMPTS:
            session.delete(challenge)
            session.commit()
            return False, "Troppi tentativi. Richiedi un nuovo codice."

        if not hmac.compare_digest(challenge.code, code.strip().upper()):
            challenge.attempts += 1
            session.commit()
            return False, "Codice errato."

        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        taken = session.query(Utente).filter(
            Utente.npub == challenge.npub, Utente.id_telegram != user_id).first()
        if taken:
            session.delete(challenge)
            session.commit()
            return False, "Questa npub è già collegata a un altro account."

        user.npub = challenge.npub
        session.delete(challenge)
        queued = queue_unlocked_badges(user_id, session)
        session.commit()
        msg = "✅ Nostr collegato!"
        if queued:
            msg += f" Sto per assegnarti {queued} badge per gli achievement che hai già."
        return True, msg
    except Exception as e:
        session.rollback()
        print(f"[Nostr] confirm_link failed: {e}")
        return False, "Errore durante la verifica, riprova."
    finally:
        session.close()


def unlink(user_id):
    session = Database().get_session()
    try:
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.npub:
            return False
        user.npub = None
        session.query(NostrLinkChallenge).filter_by(user_id=user_id).delete()
        session.commit()
        return True
    finally:
        session.close()


def get_linked_npub(user_id):
    session = Database().get_session()
    try:
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        return user.npub if user else None
    finally:
        session.close()


def process_outbox(limit=20):
    """Publish pending badge awards. Returns the number sent."""
    if not is_configured():
        return 0
    n = _sdk()
    keys = _keys()
    session = Database().get_session()
    try:
        rows = session.query(NostrBadgeOutbox).filter_by(status='pending')\
            .order_by(NostrBadgeOutbox.id).limit(limit).all()
        events, owners = [], {}
        for row in rows:
            user = session.query(Utente).filter_by(id_telegram=row.user_id).first()
            achievement = session.query(Achievement).filter_by(achievement_key=row.achievement_key).first()
            pubkey = _parse_npub(row.npub) if user and user.npub == row.npub else None
            if not pubkey or not achievement:
                # Unlinked or switched account in the meantime, or the definition is gone.
                row.status, row.error = 'failed', 'stale npub or missing achievement'
                continue
            definition = build_badge_definition(
                keys, row.achievement_key, row.tier, achievement.name, achievement.description)
            award = build_badge_award(keys, row.achievement_key, row.tier, pubkey)
            events += [definition, award]
            owners[award.id().to_hex()] = row

        accepted = asyncio.run(_publish(events)) if events else set()
        sent = 0
        for event_id, row in owners.items():
            row.attempts += 1
            if event_id in accepted:
                row.status, row.event_id, row.sent_at, row.error = 'sent', event_id, datetime.now(), None
                sent += 1
            else:
                row.error = 'no relay accepted the event'
                if row.attempts >= MAX_SEND_ATTEMPTS:
                    row.status = 'failed'
        session.commit()
        return sent
    except Exception as e:
        session.rollback()
        print(f"[Nostr] process_outbox failed: {e}")
        return 0
    finally:
        session.close()


def publish_profile(name, about, picture=None):
    """Publish the aROMa account's kind 0 profile."""
    n = _sdk()
    keys = _keys()
    metadata = n.Metadata.from_json(json.dumps(
        {k: v for k, v in {"name": name, "about": about, "picture": picture}.items() if v}))
    event = metadata.finalize(keys)
    return bool(asyncio.run(_publish([event])))
