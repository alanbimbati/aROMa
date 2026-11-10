"""The queue between the web app and the bot for fight actions: the web app asks, the bot plays and answers."""
import time
from datetime import datetime, timedelta

from database import Database
from models.webapp import WebCombatAction

# An action nobody played in time is dropped: a hit must not land minutes later, when the bot comes back.
MAX_AGE = timedelta(seconds=15)


def enqueue(user_id, chat_id, data):
    session = Database().get_session()
    try:
        row = WebCombatAction(user_id=user_id, chat_id=chat_id, data=data, status='pending', created_at=datetime.now())
        session.add(row)
        session.commit()
        return row.id
    finally:
        session.close()


def claim_pending():
    """The actions to play now, oldest first, each handed out once. One SELECT when there is nothing to do."""
    session = Database().get_session()
    try:
        rows = session.query(WebCombatAction).filter_by(status='pending').order_by(WebCombatAction.id).all()
        if not rows:
            return []
        fresh = datetime.now() - MAX_AGE
        claimed = []
        for row in rows:
            status = 'running' if row.created_at >= fresh else 'expired'
            taken = session.query(WebCombatAction).filter_by(id=row.id, status='pending').update({'status': status})
            if taken and status == 'running':
                claimed.append({'id': row.id, 'user_id': row.user_id, 'chat_id': row.chat_id, 'data': row.data})
        session.commit()
        return claimed
    finally:
        session.close()


def complete(action_id, ok, message):
    session = Database().get_session()
    try:
        session.query(WebCombatAction).filter_by(id=action_id).update(
            {'status': 'done', 'ok': 1 if ok else 0, 'message': message, 'done_at': datetime.now()})
        session.commit()
    finally:
        session.close()


def wait_result(action_id, timeout=12.0, poll=0.15):
    """(ok, message) once the bot has played the action, or None if it did not in time (the action is then dropped)."""
    deadline = time.time() + timeout
    while True:
        session = Database().get_session()
        try:
            row = session.query(WebCombatAction).filter_by(id=action_id).first()
            if row and row.status == 'done':
                return bool(row.ok), row.message or ''
            if not row or row.status == 'expired' or time.time() >= deadline:
                if row and row.status == 'pending':
                    row.status = 'expired'
                    session.commit()
                return None
        finally:
            session.close()
        time.sleep(poll)


def purge(older_than=timedelta(days=1)):
    session = Database().get_session()
    try:
        session.query(WebCombatAction).filter(WebCombatAction.created_at < datetime.now() - older_than).delete()
        session.commit()
    finally:
        session.close()
