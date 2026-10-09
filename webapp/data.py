"""What the web app shows, assembled from the same services the bot uses (so the two never disagree)."""
import json
import os
from datetime import datetime

from database import Database
from models.achievements import Achievement, UserAchievement
from models.equipment import Equipment, UserEquipment
from models.guild import Guild, GuildMember
from models.nostr import NostrBadgeOutbox
from models.seasons import Season, SeasonClaimedReward, SeasonProgress, SeasonReward
from models.stats import UserStat
from models.system import UserCharacter
from models.user import Utente
from services.achievement_tracker import AchievementTracker
from services.character_loader import get_character_loader
from services.character_service import CharacterService
from services.dungeon_service import DungeonService
from services.equipment_service import EquipmentService
from services.guild_service import GuildService
from services.item_service import ItemService
from services.season_content_service import get_season_content_service
from services.season_manager import SeasonManager
from services.skill_service import SkillService
from services.stat_build_service import StatBuildService
from services.user_service import UserService

TIERS = {0: 'free', 1: 'premium', 2: 'shop'}
TIER_ORDER = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'legendary']
STATUS_LABELS = {
    'burn': 'Ustione', 'poison': 'Veleno', 'stun': 'Stordimento', 'confusion': 'Confusione', 'freeze': 'Congelamento',
    'mind_control': 'Controllo mentale', 'bleed': 'Sanguinamento', 'slow': 'Rallentamento', 'weakness': 'Debolezza',
    'defense_up': 'Difesa +', 'buff_attack': 'Attacco +', 'buff_defense': 'Difesa +',
}
STAT_LABELS = {
    'total_kills': 'Mostri sconfitti', 'boss_kills': 'Boss sconfitti', 'high_level_kills': 'Mostri molto più forti',
    'total_damage': 'Danno totale', 'one_shots': 'Colpi singoli letali', 'critical_hits': 'Colpi critici',
    'total_heals': 'Cure effettuate', 'total_damage_taken': 'Danno subito', 'dungeons_completed': 'Dungeon completati',
    'total_wumpa_earned': 'Wumpa guadagnati', 'total_chat_exp': 'EXP da chat', 'level': 'Livello',
    'items_crafted': 'Oggetti creati', 'resources_collected': 'Risorse raccolte', 'potions_brewed': 'Pozioni create',
    'garden_plants_harvested': 'Piante raccolte', 'items_sold': 'Oggetti venduti', 'items_bought': 'Oggetti comprati',
    'dragon_balls_collected': 'Sfere del Drago', 'total_characters_unlocked': 'Personaggi sbloccati',
}


def image_name(name):
    """The file the bot looks for: the name lowercased, spaces as underscores."""
    return name.lower().replace(' ', '_')


def _character(c):
    return {
        'id': c['id'], 'name': c['nome'], 'level': c['livello'], 'tier': TIERS.get(c['lv_premium'], 'shop'),
        'price': c['price'], 'saga': c['character_group'], 'team': c.get('subgroup', ''), 'alignment': c['alignment'],
        'attack': {'name': c['special_attack_name'], 'damage': c['special_attack_damage'],
                   'mana': c['special_attack_mana_cost']},
        'crit': c['crit_chance'], 'crit_mult': c['crit_multiplier'], 'speed': c['speed'],
        'is_form': bool(c['is_transformation']), 'base_id': c['base_character_id'],
        'unique': c['max_concurrent_owners'] == 1, 'description': c['description'], 'img': image_name(c['nome']),
    }


def catalog():
    chars = get_character_loader().get_all_characters()
    return [_character(c) for c in sorted(chars, key=lambda c: (c['livello'], c['nome']))]


def character_detail(char_id):
    loader = get_character_loader()
    c = loader.get_character_by_id(char_id)
    if not c:
        return None
    out = _character(c)
    out['bonus'] = {k: c[f'bonus_{k}'] for k in ('health', 'mana', 'damage', 'resistance', 'crit', 'speed')}
    out['form_cost'] = {'mana': c['transformation_mana_cost'], 'days': c['transformation_duration_days']}
    abilities = []
    for a in SkillService().get_character_abilities(char_id):
        abilities.append({
            'name': a['name'], 'damage': a['damage'], 'mana': a['mana_cost'], 'status_key': a['status_effect'] or None,
            'status': STATUS_LABELS.get(a['status_effect'], a['status_effect'] or None),
            'status_chance': a['status_chance'], 'status_turns': a['status_duration'],
        })
    out['abilities'] = abilities
    family = [loader.get_character_by_id(i) for i in loader.get_character_family_ids(char_id)]
    out['family'] = [{'id': f['id'], 'name': f['nome'], 'level': f['livello'], 'img': image_name(f['nome'])}
                     for f in sorted((f for f in family if f), key=lambda f: f['livello'])]
    return out


def _with_session(fn):
    session = Database().get_session()
    try:
        return fn(session)
    finally:
        session.close()


def _user(session, user_id):
    return session.query(Utente).filter_by(id_telegram=user_id).first()


def title_sources(session):
    """title text -> the achievement tier that awards it, and the saga that achievement belongs to."""
    seasonal = _seasonal_groups()
    themes = {sid: theme for sid, theme in session.query(Season.id, Season.theme).all()}
    out = {}
    for a in session.query(Achievement).all():
        try:
            tiers = json.loads(a.tiers)
        except ValueError:
            continue
        group = _group_of(a, themes, seasonal)
        for tier, spec in tiers.items():
            title = (spec.get('rewards') or {}).get('title')
            if title:
                out[title] = {'achievement': a.name, 'tier': tier, 'group': group, 'category': a.category}
    return out


def profile(user_id):
    def build(session):
        u = _user(session, user_id)
        if not u:
            return None
        char = get_character_loader().get_character_by_id(u.livello_selezionato)
        try:
            titles = json.loads(u.titles) if u.titles else []
        except ValueError:
            titles = []
        floor = needed = None
        try:
            from services.leveling_service import LevelingService
            leveling = LevelingService()
            floor = leveling.get_xp_requirement(u.livello or 1)
            needed = leveling.get_xp_requirement((u.livello or 1) + 1)
        except Exception:
            pass
        projected = {}
        try:
            projected = UserService().get_projected_stats(u, session=session) or {}
        except Exception as e:
            print(f"[WEB] projected stats failed: {e}")
        guild = None
        try:
            from services.guild_service import GuildService
            g = GuildService().get_user_guild(user_id)
            guild = g.get('name') if g else None
        except Exception:
            pass
        sources = title_sources(session)
        owned = []
        for t in titles:
            src = sources.get(t, {'achievement': None, 'tier': None, 'group': 'special', 'category': None})
            owned.append({'title': t, 'equipped': t == u.title, **src})
        owned.sort(key=lambda x: (not x['equipped'], -(TIER_ORDER.index(x['tier']) if x['tier'] in TIER_ORDER else -1), x['title']))
        title_groups = [{'key': k, 'label': GROUP_LABELS.get(k, 'Altri titoli' if k == 'special' else k.replace('_', ' ').title()),
                         'count': sum(1 for x in owned if x['group'] == k)}
                        for k in sorted({x['group'] for x in owned}, key=lambda g: (g == 'special', g != 'classici', g != 'dragon_ball', g))]
        return {
            'titles_detail': owned, 'title_groups': title_groups, 'titles_available': len(sources),
            'id': u.id_telegram, 'name': u.game_name or u.nome or u.username, 'username': u.username,
            'level': u.livello, 'exp': u.exp, 'exp_floor': floor, 'exp_needed': needed, 'wumpa': u.points,
            'crystals': u.cristalli_aroma, 'premium': u.premium == 1, 'title': u.title, 'titles': titles,
            'guild': guild, 'npub': u.npub, 'stat_points': u.stat_points,
            'character': _character(char) if char else None,
            'stats': {k: v for k, v in projected.items() if isinstance(v, (int, float))},
            'radar': radar(projected, u.livello or 1),
            'presets': [{'key': k, 'label': v['desc']} for k, v in StatBuildService().get_presets().items()],
            'allocated': {'health': u.allocated_health, 'mana': u.allocated_mana, 'damage': u.allocated_damage,
                          'speed': u.allocated_speed, 'resistance': u.allocated_resistance, 'crit': u.allocated_crit},
        }
    return _with_session(build)


# ---------- stat chart ----------
# One axis per stat of the profile. The scale is fixed (what a focused build reaches at the level cap), not the
# player's own: a level 1 sees a small shape, a level 100 a large one. `now` is the same focused build at the
# player's current level, drawn as the ceiling still ahead.
RADAR_LEVEL_CAP = 100
RADAR_FOCUS = 0.4  # share of all stat points a focused build puts into one stat
RADAR_AXES = [  # key, label, base, per level, per point, hard cap
    ('max_health', 'Salute', 100, 2, 10, None), ('max_mana', 'Mana', 50, 2, 5, None),
    ('base_damage', 'Danno', 10, 1, 2, None), ('resistance', 'Resistenza', 0, 0, 1, 75),
    ('crit_chance', 'Critico', 0, 0, 1, 100), ('speed', 'Velocità', 0, 0, 1, None),
]


def radar(stats, level):
    def focused(base, per_level, per_point, cap, lv):
        lv = min(max(lv, 1), RADAR_LEVEL_CAP)
        v = base + (lv - 1) * per_level + lv * 2 * RADAR_FOCUS * per_point
        return min(v, cap) if cap else v
    return [{'key': k, 'label': label, 'value': stats.get(k, 0), 'max': focused(b, pl, pp, cap, RADAR_LEVEL_CAP),
             'now': focused(b, pl, pp, cap, level)} for k, label, b, pl, pp, cap in RADAR_AXES]


ALLOCATABLE = {'health', 'mana', 'damage', 'resistance', 'crit', 'speed'}


def allocate(user_id, stat, count=1):
    """Spend up to `count` stat points on one stat, through the bot's own rule (it stops at the resistance cap)."""
    service = UserService()
    message, spent = 'Statistica non valida.', 0
    if stat in ALLOCATABLE:
        for _ in range(max(1, min(int(count), 200))):
            session = Database().get_session()
            try:
                ok, message = service.allocate_stat_point(_user(session, user_id), stat)
            finally:
                session.close()
            if not ok:
                break
            spent += 1
    return {'ok': spent > 0, 'message': f'{spent} punti assegnati.' if spent else message, 'profile': profile(user_id)}


STAT_KEYS = ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']


def set_build(user_id, allocations=None, preset=None):
    """Replace the whole stat build (points can be taken back at any time), or apply one of the bot's presets."""
    builder = StatBuildService()
    stats = builder.start_editing(user_id)
    if not stats:
        return {'ok': False, 'message': 'Utente non trovato.'}
    if preset:
        ok, message = builder.apply_preset(user_id, preset)
        if not ok:
            return {'ok': False, 'message': message, 'profile': profile(user_id)}
    else:
        wanted = {k: int((allocations or {}).get(k, 0)) for k in STAT_KEYS}
        if any(v < 0 for v in wanted.values()) or sum(wanted.values()) > stats['total_points']:
            return {'ok': False, 'message': 'Punti insufficienti.', 'profile': profile(user_id)}
        if wanted['resistance'] > 75 or wanted['crit'] > 100:
            return {'ok': False, 'message': 'Limite raggiunto (resistenza 75%, critico 100%).', 'profile': profile(user_id)}
        stats.update(wanted)
        stats['spent_points'] = sum(wanted.values())
        message = 'Statistiche aggiornate.'
    builder.save_changes(user_id)
    return {'ok': True, 'message': message.replace('**', ''), 'profile': profile(user_id)}


def set_title(user_id, title):
    """Wear one of the titles the player owns, or none."""
    def build(session):
        u = _user(session, user_id)
        try:
            owned = json.loads(u.titles) if u and u.titles else []
        except ValueError:
            owned = []
        if title and title not in owned:
            return False
        u.title = title or None
        session.commit()
        return True
    ok = _with_session(build)
    return {'ok': ok, 'message': 'Titolo aggiornato.' if ok else 'Non possiedi questo titolo.', 'profile': profile(user_id)}


def _holders(session, me):
    """char_id -> who has it (or one of its forms) selected right now. Shared characters never appear.

    A hero and its forms count as one: if someone is Gohan, nobody else can be any Gohan.
    """
    from models.character_ownership import CharacterOwnership
    loader = get_character_loader()
    names = {u.id_telegram: u for u in session.query(Utente).all()}
    taken = {}
    for o in session.query(CharacterOwnership).all():
        used = loader.get_character_by_id(o.character_id)
        holder = names.get(o.user_id)
        if not used or not holder or used.get('max_concurrent_owners', 1) == -1:
            continue
        for member in loader.get_character_family_ids(o.character_id):
            taken[member] = {'by': holder.game_name or holder.nome or holder.username or f"Utente {o.user_id}",
                             'username': holder.username, 'form': used['nome'], 'mine': o.user_id == me}
    return taken


def my_characters(user_id):
    """Ids the user can pick right now, who holds the exclusive ones, plus level, wallet and premium flag."""
    def build(session):
        u = _user(session, user_id)
        if not u:
            return None
        taken = _holders(session, user_id)
        selectable = {c['id'] for c in CharacterService().get_available_characters(u)
                      if not (c['id'] in taken and not taken[c['id']]['mine'])}
        owned = {r[0] for r in session.query(UserCharacter.character_id).filter_by(user_id=user_id).all()}
        return {'selectable': sorted(selectable), 'owned': sorted(owned), 'level': u.livello,
                'premium': u.premium == 1, 'wumpa': u.points, 'selected': u.livello_selezionato,
                'taken': {str(k): v for k, v in taken.items()}}
    return _with_session(build)


# ---------- inventory ----------
UPGRADES = {1: 2, 2: 3, 4: 5, 5: 6, 7: 8, 8: 9}  # refined material -> next tier, 10:1 (the bot's own table)


def inventory(user_id):
    from services.crafting_service import CraftingService
    from services.item_service import ItemService
    items = ItemService()
    stuff = []
    for name, qty in items.get_inventory(user_id):
        meta = items.get_item_metadata(name)
        stuff.append({'name': name, 'quantity': qty, 'emoji': meta.get('emoji', '🎒'), 'description': meta.get('descrizione', '')})
    res = CraftingService().get_user_resources(user_id)
    refined = [{**r, 'next': UPGRADES.get(r['material_id'])} for r in res['refined'] if r['quantity']]
    names = {r['material_id']: r['name'] for r in res['refined']}
    for r in refined:
        r['next_name'] = names.get(r['next'])
        r['can_upgrade'] = bool(r['next']) and r['quantity'] >= 10
    return {'items': stuff, 'raw': [r for r in res['raw'] if r['quantity']], 'refined': refined}


def use_item(user_id, name):
    from services.item_service import ItemService
    ok, message = ItemService().use_item(user_id, name)
    return {'ok': ok, 'message': str(message).replace('**', ''), **inventory(user_id)}


def upgrade_material(user_id, source_id, count):
    from services.crafting_service import CraftingService
    target = UPGRADES.get(int(source_id))
    r = CraftingService().upgrade_material(user_id, int(source_id), target or 0, max(1, min(int(count), 100)))
    done = f"{r.get('cost')} {r.get('source_name')} → {r.get('count')} {r.get('target_name')}" if r.get('success') else None
    return {'ok': bool(r.get('success')), 'message': done or r.get('error') or 'Errore',
            **inventory(user_id)}


# ---------- character choice and forms ----------
def pick_character(user_id, char_id, buy=False):
    service = CharacterService()
    user = UserService().get_user(user_id)
    ok, message = (service.purchase_character if buy else service.equip_character)(user, int(char_id))
    return {'ok': ok, 'message': str(message).replace('**', ''), 'mine': my_characters(user_id), 'profile': profile(user_id)}


def transformations(user_id):
    from services.transformation_service import TransformationService
    service = TransformationService()
    user = UserService().get_user(user_id)
    if not user:
        return {'available': [], 'active': None}
    active = service.get_active_transformation(user)
    return {'available': service.get_available_transformations(user, user.livello_selezionato),
            'active': {'name': active['name'], 'hours': max(0, int((active['expires_at'] - datetime.now()).total_seconds() // 3600))} if active else None}


def transform(user_id, action, trans_id=None):
    from services.transformation_service import TransformationService
    service = TransformationService()
    user = UserService().get_user(user_id)
    ok, message = service.revert_transformation(user) if action == 'revert' else service.activate_transformation(user, int(trans_id or 0))
    return {'ok': ok, 'message': str(message).replace('**', ''), **transformations(user_id), 'profile': profile(user_id), 'mine': my_characters(user_id)}


STAT_SECTIONS = [
    ('combat', '⚔️ Combattimento', [
        ('total_kills', 'Mostri sconfitti'), ('boss_kills', 'Boss sconfitti'), ('high_level_kills', 'Nemici molto più forti'),
        ('total_damage', 'Danno inflitto'), ('critical_hits', 'Colpi critici'), ('one_shots', 'Uccisioni in un colpo'),
        ('total_damage_taken', 'Danno subito'), ('total_mitigated', 'Danno parato'), ('total_heals', 'Cure effettuate')]),
    ('economy', '🍑 Economia', [
        ('total_wumpa_earned', 'Wumpa guadagnati'), ('items_sold', 'Oggetti venduti'), ('items_bought', 'Oggetti comprati'),
        ('total_spent_market', 'Speso al mercato'), ('items_listed', 'Oggetti messi in vendita'), ('quick_sales', 'Vendite rapide')]),
    ('crafts', '🛠️ Mestieri', [
        ('items_crafted', 'Oggetti creati'), ('resources_collected', 'Risorse raccolte'), ('potions_brewed', 'Pozioni create'),
        ('garden_plants_planted', 'Piante seminate'), ('garden_plants_harvested', 'Piante raccolte'), ('profession_level', 'Livello mestiere')]),
    ('collection', '🏆 Collezione', [
        ('total_characters_unlocked', 'Personaggi sbloccati'), ('dragon_balls_collected', 'Sfere del Drago'),
        ('shenron_summons', 'Evocazioni di Shenron'), ('porunga_summons', 'Evocazioni di Porunga'), ('total_chat_exp', 'EXP dalla chat')]),
]
# Stats whose standing among all players is worth showing
RANKED = ['total_kills', 'boss_kills', 'total_damage', 'critical_hits', 'dungeons_completed', 'total_wumpa_earned',
          'items_crafted', 'items_sold']
RANKED_LABELS = {'dungeons_completed': 'Dungeon completati'}
_enemy_cache = {'sig': None, 'map': {}}


def _enemies():
    """kill_<name> stat key -> (name, saga, is_boss), from the mob and boss files the game itself loads."""
    import csv
    service = get_season_content_service()
    sig = service.get_runtime_signature()
    if _enemy_cache['sig'] == sig:
        return _enemy_cache['map']
    out = {}
    for kind, is_boss in (('mobs', False), ('bosses', True)):
        for path in service.get_files(kind):
            full = path if os.path.isabs(path) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
            if not os.path.exists(full):
                continue
            with open(full, newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    out['kill_' + row['nome'].lower().replace(' ', '_')] = (row['nome'], row.get('saga') or row.get('series') or '', is_boss)
    _enemy_cache.update(sig=sig, map=out)
    return out


def _standing(session, key, mine):
    """(position, players) among everyone who has the stat."""
    from sqlalchemy import func
    players = session.query(func.count(UserStat.user_id)).filter(UserStat.stat_key == key, UserStat.value > 0).scalar() or 0
    ahead = session.query(func.count(UserStat.user_id)).filter(UserStat.stat_key == key, UserStat.value > mine).scalar() or 0
    return ahead + 1, players


def stats(user_id):
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models.achievements import GameEvent
    from models.dungeon_progress import DungeonProgress

    def build(session):
        rows = {s.stat_key: s.value for s in session.query(UserStat).filter_by(user_id=user_id).all()}
        sections = []
        for key, title, items in STAT_SECTIONS:
            entries = [{'key': k, 'label': label, 'value': rows[k]} for k, label in items if rows.get(k)]
            if entries:
                sections.append({'key': key, 'title': title, 'entries': entries})

        standings = []
        for key in RANKED:
            if rows.get(key):
                position, players = _standing(session, key, rows[key])
                label = next((label for _, _, items in STAT_SECTIONS for k, label in items if k == key), None) or RANKED_LABELS.get(key)
                standings.append({'key': key, 'label': label or key, 'value': rows[key], 'position': position,
                                  'players': players, 'top_percent': max(1, round(position / max(players, 1) * 100))})

        enemy_map = _enemies()
        enemies = []
        for k, v in rows.items():
            if k.startswith('kill_') and v > 0:
                name, saga, is_boss = enemy_map.get(k, (k[5:].replace('_', ' ').title(), '', False))
                enemies.append({'name': name, 'saga': saga, 'boss': is_boss, 'value': v})
        enemies.sort(key=lambda e: -e['value'])

        defs = {}
        service = DungeonService()
        for d_id, d in service.dungeons_cache.items():
            defs[d_id] = d
        progress = []
        for p in session.query(DungeonProgress).filter_by(user_id=user_id).all():
            d = defs.get(p.dungeon_def_id)
            if d:
                progress.append({'id': p.dungeon_def_id, 'name': d['name'], 'saga': d.get('saga'), 'difficulty': d['difficulty'],
                                 'best_rank': p.best_rank, 'times': p.times_completed})
        progress.sort(key=lambda d: (d['saga'] or '', d['id']))

        # last two weeks of play, one bar per day
        since = datetime.now() - timedelta(days=13)
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)
        activity = {}
        for day, kind, n, total in session.query(
                func.date(GameEvent.timestamp), GameEvent.event_type, func.count(), func.coalesce(func.sum(GameEvent.value), 0)
        ).filter(GameEvent.user_id == user_id, GameEvent.timestamp >= since,
                 GameEvent.event_type.in_(['mob_kill', 'damage_dealt', 'dungeon_run'])).group_by(func.date(GameEvent.timestamp), GameEvent.event_type):
            d = activity.setdefault(str(day), {'kills': 0, 'damage': 0, 'dungeons': 0})
            if kind == 'mob_kill':
                d['kills'] += n
            elif kind == 'damage_dealt':
                d['damage'] += int(total)
            else:
                d['dungeons'] += n
        days = [(since + timedelta(days=i)).date().isoformat() for i in range(14)]
        timeline = [{'day': d, **activity.get(d, {'kills': 0, 'damage': 0, 'dungeons': 0})} for d in days]

        overview = [{'key': k, 'label': label, 'value': rows.get(k, 0)} for k, label in (
            ('total_kills', 'Mostri sconfitti'), ('boss_kills', 'Boss sconfitti'), ('dungeons_completed', 'Dungeon completati'),
            ('total_damage', 'Danno totale'), ('critical_hits', 'Colpi critici'), ('total_wumpa_earned', 'Wumpa guadagnati'))]
        return {'overview': overview, 'sections': sections, 'standings': standings, 'enemies': enemies[:200],
                'dungeons': progress, 'timeline': timeline}
    return _with_session(build)


GROUP_LABELS = {'classici': 'Classici', 'dragon_ball': 'Dragon Ball'}


def _group_of(achievement, season_themes, seasonal_groups):
    """Classic goals, or the ones that belong to a saga (Dragon Ball, Marvel...) and its season."""
    category = (achievement.category or '').strip().lower()
    if category == 'dragon_ball':
        return 'dragon_ball'
    if category in seasonal_groups:
        return seasonal_groups[category]
    if category == 'stagione':
        # season podium: season_<id>_podium_<n>
        parts = achievement.achievement_key.split('_')
        theme = season_themes.get(int(parts[1])) if len(parts) > 2 and parts[1].isdigit() else None
        if theme:
            return theme.strip().lower().replace(' ', '_')
    return 'classici'


def _seasonal_groups():
    """achievement category -> group, for every season pack in the manifest (marvel -> marvel)."""
    manifest = get_season_content_service()._load_manifest()
    out = {}
    for pack in manifest.get('packs', {}).values():
        theme = (pack.get('match', {}).get('theme') or '').strip()
        for category in pack.get('achievement_categories_add', []):
            out[category.strip().lower()] = theme.lower().replace(' ', '_')
            GROUP_LABELS.setdefault(theme.lower().replace(' ', '_'), theme)
    return out


def achievements(user_id):
    tracker = AchievementTracker()

    def build(session):
        inactive = set(tracker.content_service.get_inactive_seasonal_achievement_categories(session=session))
        mine = {ua.achievement_key: ua for ua in session.query(UserAchievement).filter_by(user_id=user_id).all()}
        badges = {}
        for b in session.query(NostrBadgeOutbox).filter_by(user_id=user_id).all():
            badges.setdefault((b.achievement_key, b.tier), b.status)
        seasonal = _seasonal_groups()
        themes = {sid: theme for sid, theme in session.query(Season.id, Season.theme).all()}
        out = []
        for a in session.query(Achievement).all():
            owned = mine.get(a.achievement_key)
            if not owned or not owned.current_tier:
                if not tracker._is_achievement_available(a, inactive):
                    continue  # another season's goals stay hidden until earned
            try:
                tiers = json.loads(a.tiers)
            except ValueError:
                tiers = {}
            current = owned.current_tier if owned else None
            ladder = [t for t in TIER_ORDER if t in tiers]
            nxt = next((t for t in ladder if current is None or TIER_ORDER.index(t) > TIER_ORDER.index(current)), None)
            out.append({
                'key': a.achievement_key, 'name': a.name, 'description': a.description, 'category': a.category,
                'group': _group_of(a, themes, seasonal),
                'current': current, 'next': nxt, 'next_threshold': tiers[nxt]['threshold'] if nxt else None,
                'progress': owned.progress_value if owned else 0,
                'tiers': [{'tier': t, 'threshold': tiers[t].get('threshold'),
                           'reward': tiers[t].get('rewards', {}), 'badge': badges.get((a.achievement_key, t))}
                          for t in ladder],
            })
        out.sort(key=lambda x: (x['current'] is None, x['category'] or '', x['name']))
        groups = []
        for key in sorted({a['group'] for a in out}, key=lambda g: (g != 'classici', g != 'dragon_ball', g)):
            members = [a for a in out if a['group'] == key]
            groups.append({'key': key, 'label': GROUP_LABELS.get(key, key.replace('_', ' ').title()),
                           'total': len(members), 'unlocked': sum(1 for a in members if a['current'])})
        return {'groups': groups, 'items': out}
    return _with_session(build)


def season(user_id):
    manager = SeasonManager()

    def build(session):
        s = manager.get_active_season(session=session)
        ranking, _ = manager.get_season_ranking(limit=20)
        if not s:
            return {'active': False}
        prog = session.query(SeasonProgress).filter_by(user_id=user_id, season_id=s.id).first()
        claimed = {r[0] for r in session.query(SeasonClaimedReward.reward_id).filter_by(
            user_id=user_id, season_id=s.id).all()}
        level = prog.current_level if prog else 1
        premium = bool(prog and prog.has_premium_pass) or bool((_user(session, user_id) or Utente()).premium == 1)
        rewards = []
        for r in session.query(SeasonReward).filter_by(season_id=s.id).order_by(
                SeasonReward.level_required, SeasonReward.is_premium).all():
            entry = {'rank': r.level_required, 'premium': bool(r.is_premium), 'type': r.reward_type,
                     'name': r.reward_name, 'icon': r.icon, 'value': r.reward_value,
                     'claimed': r.id in claimed, 'reachable': r.level_required <= level,
                     'locked': bool(r.is_premium) and not premium}
            if r.reward_type == 'character':
                char = get_character_loader().get_character_by_id(int(r.reward_value))
                if char:
                    entry.update(char_id=char['id'], img=image_name(char['nome']), char_level=char['livello'],
                                 tier=TIERS.get(char['lv_premium'], 'shop'))
            rewards.append(entry)
        return {
            'active': True, 'name': s.name, 'theme': s.theme, 'ends': s.end_date.isoformat(),
            'rank': level, 'exp': prog.current_exp if prog else 0, 'total_exp': (prog.total_exp or 0) if prog else 0,
            'exp_needed': 100 * (level ** 2), 'max_rank': manager.MAX_RANK, 'premium': premium,
            'final_reward': s.final_reward_name, 'rewards': rewards,
            'ranking': [{'name': r.get('game_name') or r.get('nome') or r.get('username'), 'rank': r['level'],
                         'exp': r['exp'], 'level': r['user_level']} for r in (ranking or [])],
        }
    return _with_session(build)


def dungeons(user_id):
    service = DungeonService()

    def build(session):
        service.refresh_cache_if_needed()
        progress = {p.dungeon_def_id: p for p in service.get_user_progress(user_id, session=session)}
        out = []
        for d_id in service.get_active_dungeon_ids(session=session):
            d = service.dungeons_cache[d_id]
            p = progress.get(d_id)
            out.append({
                'id': d_id, 'name': d['name'], 'difficulty': d['difficulty'], 'saga': d.get('saga'),
                'description': d.get('description'), 'stages': len(d['steps']), 'rewards': d['rewards'],
                'unlocked': service.can_access_dungeon(user_id, d_id, session=session),
                'played_today': service.has_played_today(session, user_id, d_id),
                'best_rank': p.best_rank if p else None, 'times_completed': p.times_completed if p else 0,
            })
        return out
    return _with_session(build)


def start_solo_dungeon(user_id, dungeon_id):
    """Open a solo run in the player's private chat with the bot and send the start button there: the fight itself
    is driven by the bot, which is the only process that talks to the chat."""
    import json as _json
    import urllib.request
    from settings import BOT_TOKEN
    service = DungeonService()
    service.refresh_cache_if_needed()
    real_id, message = service.create_dungeon(user_id, int(dungeon_id), user_id, is_solo=True)
    if not real_id:
        return {'ok': False, 'message': message.replace('**', '')}
    name = service.dungeons_cache[int(dungeon_id)]['name']
    payload = {'chat_id': user_id, 'parse_mode': 'Markdown',
               'text': f"🏰 **DUNGEON SOLO: {name}**\nPronto a iniziare l'avventura?",
               'reply_markup': {'inline_keyboard': [[{'text': '▶️ Avvia Dungeon', 'callback_data': f'dungeon_start|{real_id}'}]]}}
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', _json.dumps(payload).encode(),
                                     {'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print(f"[WEB] dungeon lobby message failed: {e}")
        return {'ok': False, 'message': "Non riesco a scriverti nel bot: aprilo e premi /start, poi riprova."}
    return {'ok': True, 'message': f"{name}: ti ho scritto nel bot, premi «Avvia Dungeon»."}


def nostr_status(user_id):
    """Link state and how many badges went out / are waiting for this user's current npub."""
    from services import nostr_service

    def build(session):
        u = _user(session, user_id)
        npub = u.npub if u else None
        counts = {'sent': 0, 'pending': 0, 'failed': 0}
        if npub:
            for status, n in session.query(NostrBadgeOutbox.status, func_count()).filter_by(
                    user_id=user_id, npub=npub).group_by(NostrBadgeOutbox.status).all():
                counts[status] = n
        return {'enabled': nostr_service.is_configured(), 'npub': npub, 'badges': counts}
    return _with_session(build)


def func_count():
    from sqlalchemy import func
    return func.count()


# ---------- equipment ----------
SLOTS = [('head', 'Testa'), ('chest', 'Torso'), ('main_hand', 'Arma'), ('legs', 'Gambe'), ('feet', 'Piedi'),
         ('accessory1', 'Accessorio 1'), ('accessory2', 'Accessorio 2')]
RARITIES = {1: 'Comune', 2: 'Non comune', 3: 'Raro', 4: 'Epico', 5: 'Leggendario'}
STAT_NAMES = {'health': 'Salute', 'max_health': 'Salute', 'mana': 'Mana', 'max_mana': 'Mana', 'attack': 'Danno',
              'base_damage': 'Danno', 'defense': 'Resistenza', 'resistance': 'Resistenza', 'crit': 'Critico',
              'crit_chance': 'Critico', 'speed': 'Velocità', 'all_stats': 'Tutte le statistiche'}


def _stats(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = {}
    return {STAT_NAMES.get(k, k): v for k, v in (raw or {}).items()} if isinstance(raw, dict) else {}


def equipment(user_id):
    """Everything the user owns, what is worn where, and what the worn items add up to."""
    def build(session):
        user = _user(session, user_id)
        rows = EquipmentService().get_user_inventory(user_id, session=session)
        items = []
        for owned, item in rows:
            items.append({
                'id': owned.id, 'name': item.name, 'slot': item.slot, 'rarity': max(int(owned.rarity or 1), int(item.rarity or 1)),  # the instance column defaults to 1 when unset
                'min_level': item.min_level, 'stats': _stats(owned.stats_json or item.stats_json),
                'set': item.set_name or None, 'description': item.description, 'equipped': bool(owned.equipped),
                'worn_in': owned.slot_equipped if owned.equipped else None,
            })
        items.sort(key=lambda i: (-i['rarity'], i['name']))
        totals = {}
        for k, v in EquipmentService().calculate_equipment_stats(user_id, session=session).items():
            label = STAT_NAMES.get(k, k)
            totals[label] = totals.get(label, 0) + v
        sets = {}
        for i in items:
            if i['set'] and i['equipped']:
                sets[i['set']] = sets.get(i['set'], 0) + 1
        return {'level': user.livello if user else 1, 'slots': [{'key': k, 'label': l} for k, l in SLOTS],
                'rarities': RARITIES, 'items': items, 'totals': totals,
                'sets': [{'name': n, 'worn': c, 'total': sum(1 for i in items if i['set'] == n)} for n, c in sets.items()]}
    return _with_session(build)


def equip(user_id, item_id, wear):
    service = EquipmentService()
    ok, message = (service.equip_item if wear else service.unequip_item)(user_id, item_id)
    return {'ok': ok, 'message': message, **equipment(user_id)}


# ---------- guild ----------
# (key, name, what it gives, level column, upgrade method, top level)
BUILDINGS = [
    ('village', 'Villaggio', 'Più posti per i membri', 'village_level', 'expand_village', 5),
    ('inn', 'Locanda', 'Recupero più veloce', 'inn_level', 'upgrade_inn', None),
    ('armory', 'Armeria', 'Equipaggiamento di gilda', 'armory_level', 'upgrade_armory', 5),
    ('brewery', 'Birrificio', 'Bevande e pozioni potenziate', 'brewery_level', 'upgrade_brewery', None),
    ('laboratory', 'Laboratorio', 'Alchimia', 'laboratory_level', 'upgrade_laboratory', None),
    ('garden', 'Giardino', 'Coltivazione', 'garden_level', 'upgrade_garden', None),
    ('dragon_stables', 'Stalle dei draghi', 'Ricariche più brevi', 'dragon_stables_level', 'upgrade_dragon_stables', None),
    ('ancient_temple', 'Tempio antico', 'Bonus al critico', 'ancient_temple_level', 'upgrade_ancient_temple', None),
    ('magic_library', 'Biblioteca magica', 'Bonus al mana', 'magic_library_level', 'upgrade_magic_library', None),
    ('bordello', 'Bordello delle Elfe', 'Vigore', 'bordello_level', 'upgrade_bordello', None),
]


BUILDING_IMAGES = {'village': 'main', 'inn': 'inn', 'armory': 'armory', 'brewery': 'brewery', 'laboratory': 'laboratory',
                   'garden': 'garden', 'dragon_stables': 'stables', 'ancient_temple': 'temple',
                   'magic_library': 'library', 'bordello': 'bordello'}
DRINKS = [('beer', 'Birra', 1, 0), ('whiskey', 'Whiskey', 3, 50), ('ambrosia', 'Ambrosia', 5, 500), ('mead', 'Idromele', 7, 1000),
          ('dragon_blood', 'Sangue di drago', 9, 5000), ('yggdrasil', 'Yggdrasil', 10, 10000)]
COMPANY = [('fairy', 'Fatina', 1, 100), ('elf', 'Elfa', 3, 500), ('nymph', 'Ninfa', 5, 1500), ('succubus', 'Succube', 7, 5000)]
SEEDS = ['Semi di Wumpa', "Seme d'Erba Verde", "Seme d'Erba Blu", "Seme d'Erba Gialla"]
OPEN_PANEL = ('garden', 'laboratory', 'refinery', 'market', 'armory')  # multi-slot: they open a panel of their own


def _act(action, label, enabled=True, reason=None, option=None):
    return {'action': action, 'label': label, 'option': option, 'enabled': enabled, 'reason': None if enabled else reason}


def _building_uses(user, mine, key, level):
    """What the player can press in a building right now, each with why it is off if it is."""
    from datetime import datetime
    now = datetime.now()
    if not level:
        return []
    same_day = lambda t: bool(t and t.date() == now.date())
    if key == 'inn':
        if user.resting_since:
            return [_act('wake', 'Svegliati')]
        busy = user.last_attack_time and (now - user.last_attack_time).total_seconds() < 600
        wait = int(600 - (now - user.last_attack_time).total_seconds()) if busy else 0
        return [_act('rest', 'Riposa', not busy, f'In combattimento: aspetta {wait // 60}m {wait % 60}s')]
    if key == 'ancient_temple':
        return [_act('pray', 'Prega (bonus critico)')]
    if key == 'magic_library':
        return [_act('study', 'Studia (mana)')]
    if key == 'brewery':
        done = same_day(user.last_beer_usage)
        out = []
        for opt, label, lvl, cost in DRINKS:
            reason = (f'Birrificio Lv. {lvl}' if (mine.get('brewery_level') or 0) < lvl else 'Già bevuto oggi' if done
                      else f'Servono {cost} Wumpa' if user.points < cost else None)
            out.append(_act('drink', f'{label}{f" · 🍑{cost}" if cost else ""}', reason is None, reason, opt))
        return out
    if key == 'bordello':
        free = not same_day(user.last_brothel_usage)
        out = []
        for opt, label, lvl, cost in COMPANY:
            price = 0 if free else cost
            reason = (f'Bordello Lv. {lvl}' if (mine.get('bordello_level') or 0) < lvl
                      else f'Servono {price} Wumpa' if user.points < price else None)
            out.append(_act('vigore', f'{label} · {"gratis oggi" if free else f"🍑{price}"}', reason is None, reason, opt))
        return out
    if key == 'dragon_stables':
        soon = user.last_egg_nurture and (now - user.last_egg_nurture).total_seconds() < 3600
        return [_act('egg_nurture', "Accudisci l'uovo", not soon, 'Riprova tra meno di un\'ora')]
    if key in OPEN_PANEL:
        return [_act('open', {'garden': 'Apri il giardino', 'laboratory': 'Apri il laboratorio', 'refinery': 'Apri la raffineria', 'market': 'Apri il mercato', 'armory': 'Apri la forgia'}[key])]
    return []


def _member_image(session, user_id):
    u = _user(session, user_id)
    c = get_character_loader().get_character_by_id(u.livello_selezionato) if u else None
    return image_name(c['nome']) if c else None


def guild(user_id):
    service = GuildService()

    def build(session):
        user = _user(session, user_id)
        mine = service.get_user_guild(user_id)
        wumpa = user.points if user else 0
        if not mine:
            return {'guild': None, 'wumpa': wumpa, 'level': user.livello if user else 1, 'guilds': service.get_guilds_list()}
        members = service.get_guild_members(mine['id'])
        order = {'Leader': 0, 'Officer': 1}
        members.sort(key=lambda m: (order.get(m['role'], 2), -m['level']))
        leader = mine['role'] == 'Leader'
        return {
            'wumpa': wumpa,
            'guild': {
                'id': mine['id'], 'name': mine['name'], 'emblem': mine['emblem'], 'description': mine['description'],
                'bank': mine['wumpa_bank'], 'limit': mine['member_limit'], 'role': mine['role'], 'leader': leader,
                'members': [{'name': m['name'], 'role': m['role'], 'level': m['level'], 'me': m['user_id'] == user_id,
                             'img': _member_image(session, m['user_id'])} for m in members],
                'buildings': [{'key': k, 'name': n, 'gives': g, 'level': mine.get(col) or 0, 'top': top,
                               'maxed': bool(top and (mine.get(col) or 0) >= top), 'img': BUILDING_IMAGES.get(k),
                               'use': _building_uses(user, mine, k, mine.get(col) or 0)}
                              for k, n, g, col, _, top in BUILDINGS] + [{
                    'key': 'refinery', 'name': 'Raffineria', 'gives': 'Raffina, distilla e composta i materiali', 'level': mine.get('armory_level') or 0,
                    'top': None, 'maxed': True, 'img': 'armory', 'fixed': True,
                    'use': _building_uses(user, mine, 'refinery', mine.get('armory_level') or 0)},
                    {'key': 'market', 'name': 'Mercato', 'gives': 'Cerca e compra ciò che vendono gli altri giocatori', 'level': 1, 'top': None,
                     'maxed': True, 'img': None, 'icon': '🏪', 'fixed': True, 'use': _building_uses(user, mine, 'market', 1)}],
                'egg': service.get_active_egg(mine['id']) if mine.get('dragon_stables_level') else None,
                'egg_shop': [{'type': t, 'label': l, 'cost': c, 'nurtures': n, 'affordable': mine['wumpa_bank'] >= c} for t, l, c, n in EGGS],
                'stash': [{'name': n, 'quantity': q} for n, q in service.get_guild_inventory(mine['id'])],
                'carry': [{'name': n, 'quantity': q} for n, q in ItemService().get_inventory(user_id)],
                'ranking': [{'name': x['name'], 'level': x['level'], 'members': x['members'], 'mine': x['id'] == mine['id']}
                            for x in service.get_guilds_list()[:10]],
            },
        }
    return _with_session(build)


def workshop(user_id, kind):
    """Garden slots or the alchemy queue and recipes, for the panel that opens from the guild page."""
    from datetime import datetime
    if kind == 'garden':
        from services.cultivation_service import CultivationService
        cs = CultivationService()
        cs.check_growth(user_id)
        slots, cap = cs.get_garden_slots(user_id)
        now = datetime.now()
        return {'kind': 'garden', 'capacity': cap, 'seeds': SEEDS, 'slots': [
            {'id': x['slot_id'], 'status': x['status'], 'moisture': x.get('moisture', 100), 'plant': x.get('plant_name') or x.get('seed_type'),
             'minutes': max(0, int((x['completion_time'] - now).total_seconds() / 60)) if x.get('completion_time') and x['status'] == 'growing' else 0}
            for x in slots]}
    if kind == 'laboratory':
        from services.alchemy_service import AlchemyService
        from services.crafting_service import CraftingService
        alchemy, crafting = AlchemyService(), CraftingService()
        recipes = []
        for name, r in alchemy.get_recipes().items():
            need = [{'name': n, 'need': q, 'have': crafting.get_resource_quantity(user_id, n)} for n, q in r['required_resources'].items()]
            recipes.append({'name': name, 'minutes': round(r['crafting_time'] / 60), 'needs': need, 'can': all(x['have'] >= x['need'] for x in need)})
        return {'kind': 'laboratory', 'recipes': recipes, 'queue': alchemy.get_alchemy_status(user_id)}
    if kind == 'refinery':
        return _refinery(user_id)
    if kind == 'market':
        return market(user_id)
    if kind == 'armory':
        return _forge(user_id)
    return None


def _forge(user_id):
    """The armory's forge: what the guild is crafting, and what this player could start with their materials."""
    from sqlalchemy import text
    from services.crafting_service import CraftingService
    crafting = CraftingService()
    mine = GuildService().get_user_guild(user_id)
    level = (mine or {}).get('armory_level') or 0
    have = {r['name']: r['quantity'] for r in crafting.get_user_resources(user_id)['refined']}
    session = crafting.db.get_session()
    try:
        now = datetime.now()
        jobs = [{'name': n, 'minutes': max(0, round((done - now).total_seconds() / 60)), 'ready': done <= now, 'mine': uid == user_id}
                for done, n, uid in session.execute(text(
                    "SELECT cq.completion_time, e.name, cq.user_id FROM crafting_queue cq JOIN equipment e ON e.id = cq.equipment_id "
                    "WHERE cq.guild_id = :g AND cq.status = 'in_progress' ORDER BY cq.completion_time"), {'g': mine['id'] if mine else -1}).fetchall()]
        rows = session.execute(text(
            "SELECT id, name, rarity, min_level, crafting_time, crafting_requirements, slot, set_name FROM equipment "
            "WHERE rarity <= :lvl AND crafting_requirements IS NOT NULL ORDER BY set_name, rarity, min_level"), {'lvl': level}).fetchall()
    finally:
        session.close()
    items = []
    for eid, name, rarity, min_level, seconds, req, slot, set_name in rows:
        try:
            need = json.loads(req) if isinstance(req, str) else (req or {})
        except ValueError:
            continue
        if not need:
            continue
        needs = [{'name': n, 'need': q, 'have': have.get(n, 0)} for n, q in need.items()]
        items.append({'id': eid, 'name': name, 'rarity': rarity, 'min_level': min_level, 'minutes': round((seconds or 0) / 60),
                      'slot': slot, 'set': set_name or 'Vario', 'needs': needs, 'can': all(x['have'] >= x['need'] for x in needs)})
    return {'kind': 'armory', 'level': level, 'slots': level, 'free': max(0, level - len(jobs)), 'jobs': jobs, 'items': items,
            'ready': sum(1 for j in jobs if j['ready'] and j['mine'])}


MARKET_PAGE = 8


def market(user_id, q='', page=1):
    """What other players are selling right now, searchable by item name."""
    from datetime import datetime
    from sqlalchemy.orm import joinedload
    from models.market import MarketListing

    def build(session):
        query = session.query(MarketListing).options(joinedload(MarketListing.seller)).filter(
            MarketListing.status == 'active', MarketListing.expires_at > datetime.now())
        q_clean = (q or '').strip()[:60]
        if q_clean:
            query = query.filter(MarketListing.item_name.ilike(f"%{q_clean}%"))
        total = query.count()
        rows = query.order_by(MarketListing.created_at.desc()).offset((max(page, 1) - 1) * MARKET_PAGE).limit(MARKET_PAGE).all()
        from services.crafting_service import CraftingService
        from services.item_service import ItemService
        sellable = [{'name': n, 'quantity': q} for n, q in ItemService().get_inventory(user_id)] + \
                   [{'name': r['name'], 'quantity': r['quantity']} for r in CraftingService().get_user_resources(user_id)['raw'] if r['quantity']]
        return {'kind': 'market', 'sellable': sellable, 'q': q_clean, 'page': max(page, 1), 'pages': max(1, -(-total // MARKET_PAGE)), 'total': total,
                'wumpa': (_user(session, user_id).points if _user(session, user_id) else 0),
                'listings': [{'id': r.id, 'item': r.item_name, 'quantity': r.quantity, 'unit': r.price_per_unit,
                              'total': r.price_per_unit * r.quantity, 'mine': r.seller_id == user_id,
                              'seller': (r.seller.game_name or r.seller.nome or r.seller.username) if r.seller else 'Utente',
                              'hours': max(0, int((r.expires_at - datetime.now()).total_seconds() // 3600))} for r in rows]}
    return _with_session(build)


def market_sell(user_id, item, quantity, price, days=7):
    from services.market_service import MarketService
    quantity, price, days = int(quantity), int(price), max(1, min(int(days), 30))
    if quantity < 1 or price < 1:
        return {'ok': False, 'message': 'Quantità e prezzo devono essere positivi.', **market(user_id)}
    ok, message = MarketService().list_item(user_id, item, quantity, price, days)
    return {'ok': ok, 'message': str(message).replace('**', ''), **market(user_id)}


GUIDES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'guides')
GUIDE_TITLES = {'fight_system': ('⚔️', 'Sistema di combattimento'), 'dungeons': ('🏰', 'Dungeon'), 'alchemy': ('⚗️', 'Alchimia'),
                'garden': ('🌻', 'Giardino e coltivazioni'), 'refinery': ('💎', 'Raffineria'), 'crafting': ('🔨', 'Crafting e forgia'),
                'stats_allocation': ('📊', 'Allocazione statistiche'), 'season_system': ('🍂', 'Sistema stagionale'),
                'achievements': ('🏆', 'Achievement'), 'guild_village': ('🏘️', 'Gilda e villaggio'), 'dragon_eggs': ('🥚', 'Uova di drago')}


def guides():
    names = [n[:-3] for n in sorted(os.listdir(GUIDES_DIR)) if n.endswith('.md')] if os.path.isdir(GUIDES_DIR) else []
    return [{'key': n, 'icon': GUIDE_TITLES[n][0], 'title': GUIDE_TITLES[n][1]} for n in GUIDE_TITLES if n in names]


def guide(name):
    if name not in GUIDE_TITLES:
        return None
    path = os.path.join(GUIDES_DIR, f'{name}.md')
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return {'key': name, 'icon': GUIDE_TITLES[name][0], 'title': GUIDE_TITLES[name][1], 'text': f.read()}


EGGS = [('common', 'Comune', 5000, 50), ('rare', 'Raro', 15000, 200), ('epic', 'Epico', 50000, 500)]


REFINERY = [('equipment', '💎 Raffineria', 'Raffina', 'armorsmith', 'Materiali grezzi → componenti per il Fabbro'),
            ('alchemy', '⚗️ Distillazione', 'Distilla', 'alchemy', 'Essenze di mostri e piante → ingredienti per pozioni'),
            ('garden', '💩 Compostiera', 'Composta', 'garden', 'Scarti ed erbe → fertilizzanti e materiali alchemici')]


def _refinery(user_id):
    from datetime import datetime
    from sqlalchemy import text
    from services.crafting_service import CraftingService
    crafting = CraftingService()
    mine = GuildService().get_user_guild(user_id)
    sections = []
    session = crafting.db.get_session()
    try:
        for cat, title, verb, prof, blurb in REFINERY:
            daily = crafting.get_daily_refinable_resource(category=cat)
            info = crafting.get_profession_info(user_id, profession_name=prof)
            jobs, ready = [], 0
            if daily and mine:
                now = datetime.now()
                for done, name, qty, uid in session.execute(text(
                        "SELECT rq.completion_time, r.name, rq.quantity, rq.user_id FROM refinery_queue rq JOIN resources r ON r.id = rq.resource_id "
                        "WHERE rq.guild_id = :g AND rq.resource_id = :r AND rq.status IN ('in_progress', 'completed') ORDER BY rq.completion_time"),
                        {'g': mine['id'], 'r': daily['id']}).fetchall():
                    left = (done - now).total_seconds()
                    jobs.append({'name': name, 'qty': qty, 'minutes': max(0, round(left / 60)), 'ready': left <= 0, 'mine': uid == user_id})
                    ready += 1 if left <= 0 and uid == user_id else 0
            sections.append({'category': cat, 'title': title, 'verb': verb, 'blurb': blurb, 'level': info['level'], 'xp': info['xp'],
                             'resource': {'id': daily['id'], 'name': daily['name'], 'have': crafting.get_resource_quantity(user_id, daily['name'])} if daily else None,
                             'jobs': jobs, 'ready': ready})
    finally:
        session.close()
    return {'kind': 'refinery', 'sections': sections}


def guild_action(user_id, action, amount=None, guild_id=None, building=None, option=None, slot=None):
    result = _guild_action(user_id, action, amount, guild_id, building, option, slot)
    if building in OPEN_PANEL and result.get('ok') is not None:
        result['workshop'] = workshop(user_id, building)
    return result


def _guild_action(user_id, action, amount=None, guild_id=None, building=None, option=None, slot=None):
    """One guild move, answered with the new state and the game's own message (it says what a failed upgrade costs)."""
    service = GuildService()
    if action == 'deposit':
        ok, message = service.deposit_wumpa(user_id, int(amount or 0))
    elif action == 'withdraw':
        ok, message = service.withdraw_wumpa(user_id, int(amount or 0))
    elif action == 'join':
        ok, message = service.join_guild(user_id, int(guild_id or 0))
    elif action == 'leave':
        ok, message = service.leave_guild(user_id)
    elif action == 'pray':
        ok, message = service.pray_at_temple(user_id)
    elif action == 'study':
        ok, message = service.study_at_library(user_id)
    elif action == 'drink':
        ok, message = service.buy_guild_drink(user_id, option or 'beer')
    elif action == 'vigore':
        ok, message = service.apply_vigore_bonus(user_id, option or 'fairy')
    elif action == 'egg_nurture':
        ok, message = service.nurture_egg(user_id)
    elif action == 'rest':
        ok, message = UserService().start_resting(user_id)
    elif action == 'wake':
        mine = service.get_user_guild(user_id)
        ok, message = UserService().stop_resting(user_id, recovery_multiplier=1.0 + (mine['inn_level'] * 0.5 if mine else 0))
    elif action in ('plant', 'water', 'harvest', 'clear'):
        from services.cultivation_service import CultivationService
        cs = CultivationService()
        ok, message = {'plant': lambda: cs.plant_seed(user_id, int(slot or 0), option), 'water': lambda: cs.water_plant(user_id, int(slot or 0)),
                       'harvest': lambda: cs.harvest_plant(user_id, int(slot or 0)), 'clear': lambda: cs.clear_rotten_slot(user_id, int(slot or 0))}[action]()
    elif action in ('brew', 'claim'):
        from services.alchemy_service import AlchemyService
        alchemy = AlchemyService()
        ok, message = alchemy.brew_potion(user_id, option) if action == 'brew' else alchemy.claim_potions(user_id)
    elif action in ('refine', 'refine_claim'):
        from services.crafting_service import CraftingService
        crafting = CraftingService()
        mine = service.get_user_guild(user_id)
        if not mine:
            return {'ok': False, 'message': 'Non fai parte di nessuna gilda!', **guild(user_id)}
        category, _, res = (option or '').partition(':')
        if action == 'refine':
            r = crafting.start_refinement(mine['id'], user_id, int(res or 0), int(amount or 0), category=category)
            ok, message = r['success'], 'Lavoro avviato!' if r['success'] else r.get('error', 'Errore')
        else:
            r = crafting.claim_user_refinements(user_id, category=category or None)
            ok = r['success']
            message = ('Ritirato: ' + ', '.join(f'{m} ×{q}' for m, q in r['totals'].items() if q > 0)) if ok else r.get('error', 'Errore')
    elif action == 'found':
        r = service.create_guild(user_id, (option or '').strip()[:32])
        ok, message = r[0], r[1]
    elif action == 'rename':
        ok, message = service.rename_guild(user_id, (option or '').strip()[:32]) if (option or '').strip() else (False, 'Scrivi un nome.')
    elif action == 'describe':
        ok, message = service.set_guild_description(user_id, (option or '').strip())
    elif action == 'emblem':
        ok, message = service.set_guild_emblem(user_id, (option or '').strip()[:8])
    elif action == 'disband':
        ok, message = service.delete_guild(user_id)
    elif action == 'stash_deposit':
        ok, message = service.deposit_item(user_id, option or '', max(1, int(amount or 1)))
    elif action == 'stash_withdraw':
        ok, message = service.withdraw_item(user_id, option or '', max(1, int(amount or 1)))
    elif action == 'egg_buy':
        ok, message = service.buy_egg(user_id, option or '')
    elif action in ('market_buy', 'market_cancel'):
        from services.market_service import MarketService
        market_service = MarketService()
        ok, message = (market_service.buy_item if action == 'market_buy' else market_service.cancel_listing)(user_id, int(option or 0))
        message = message.replace('**', '')
    elif action in ('craft', 'craft_claim'):
        from services.crafting_service import CraftingService
        crafting = CraftingService()
        mine = service.get_user_guild(user_id)
        if not mine:
            return {'ok': False, 'message': 'Non fai parte di nessuna gilda!', **guild(user_id)}
        if action == 'craft':
            r = crafting.start_crafting(mine['id'], user_id, int(option or 0))
            ok, message = r['success'], (f"{r['equipment_name']}: pronto tra {round(r['crafting_time'] / 60)} min." if r['success'] else r.get('error', 'Errore'))
        else:
            done = [x for x in crafting.process_queue() if x.get('success')]
            ok = bool(done)
            message = ('Ritirato: ' + ', '.join(f"{x.get('item_name')} ({x.get('quality', 'Normal')})" for x in done)) if ok else 'Niente da ritirare.'
        message = message.replace('**', '')
    elif action == 'workshop':
        return {'ok': True, 'message': '', **guild(user_id)}
    elif action == 'upgrade':
        method = next((m for k, _, _, _, m, _ in BUILDINGS if k == building), None)
        if not method:
            return {'ok': False, 'message': 'Edificio sconosciuto.', **guild(user_id)}
        ok, message = getattr(service, method)(user_id)
    else:
        return {'ok': False, 'message': 'Azione sconosciuta.', **guild(user_id)}
    return {'ok': ok, 'message': message, **guild(user_id)}
