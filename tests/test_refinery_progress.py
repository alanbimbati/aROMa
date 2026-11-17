import random

from database import Database
from models.stats import UserStat
from services.crafting_service import CraftingService, _round_randomly


def _stat(user_id, key):
    session = Database().get_session()
    try:
        row = session.query(UserStat).filter_by(user_id=user_id, stat_key=key).first()
        return row.value if row else None
    finally:
        session.close()


def test_armorsmith_xp_adds_up_instead_of_being_overwritten():
    cs, uid = CraftingService(), 777000111
    cs.add_profession_xp(uid, 80, profession_name='armorsmith')
    cs.add_profession_xp(uid, 80, profession_name='armorsmith')
    info = cs.get_profession_info(uid, 'armorsmith')
    assert info['xp'] == 160 and info['level'] == 2


def test_an_alchemy_level_up_does_not_become_the_armorsmith_level():
    cs, uid = CraftingService(), 777000112
    from models.user import Utente
    session = Database().get_session()
    try:
        session.add(Utente(id_telegram=uid, nome='Alchimista', username='alchimista_test', livello=10))
        session.commit()
    finally:
        session.close()
    cs.add_profession_xp(uid, 5000, profession_name='alchemy')
    from services.stat_aggregator import StatAggregator
    session = Database().get_session()
    try:
        from models.achievements import GameEvent
        events = session.query(GameEvent).filter_by(user_id=uid).all()
    finally:
        session.close()
    StatAggregator().process_events(events)
    assert cs.get_profession_info(uid, 'armorsmith')['level'] == 1
    assert _stat(uid, 'profession_level') is None


def test_a_small_batch_keeps_its_chance_at_rare_materials():
    random.seed(1)
    assert sum(_round_randomly(0.3) for _ in range(10000)) in range(2800, 3200)
    assert _round_randomly(2.0) == 2
