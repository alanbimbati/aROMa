"""What a dungeon pays, from its recommended level. Pure functions, shared by the game and the data script."""

KILL_SHARE = 0.6        # of a dungeon's purse, paid out kill by kill (a boss counts as BOSS_UNITS enemies)
BOSS_UNITS = 3
TEAM_BONUS = 0.25       # every extra player who fights makes everyone's reward 25% bigger...
TEAM_BONUS_CAP = 1.0    # ...up to double


def dungeons_per_level(level):
    """How many dungeons made for a player's level it takes to climb one level: 2 at first, slowly more
    (about 3.5 at 50, 6 at 100), so the later levels ask for more than the first ones do."""
    return 2 + 4 * ((min(max(1, int(level)), 100) - 1) / 99) ** 2


def budget(level):
    """(exp, wumpa) a lone player earns by clearing a dungeon made for their level: a level's worth of EXP divided
    by dungeons_per_level (the curve is 10 * level^2.5), and a purse that shrinks by the same factor."""
    level = max(1, int(level))
    n = dungeons_per_level(level)
    exp = 10 * ((level + 1) ** 2.5 - level ** 2.5) / n
    wumpa = (40 + 12 * level + 0.15 * level ** 2) * 2 / n
    return int(exp), int(wumpa)


def player_scale(level, player_level):
    """Share of the dungeon's budget a player below its level gets: a dungeon is paid by the player's own level step
    (up to 1.5x it for a harder dungeon), so three dungeons made for level 35 do not take a level-1 player to level
    10. Never above 1: a stronger player earns what the dungeon pays, no more."""
    pl, level = max(1, int(player_level or 1)), max(1, int(level))
    if pl >= level:
        return 1.0
    own = (10 * ((pl + 1) ** 2.5 - pl ** 2.5) / dungeons_per_level(pl)) * min(1.5, level / pl)
    return min(1.0, own / budget(level)[0])


def team_bonus(fighters):
    return 1 + min(TEAM_BONUS_CAP, TEAM_BONUS * (max(1, fighters) - 1))


def completion(level, fighters=1, player_level=None):
    """What each participant gets when the dungeon is cleared."""
    exp, wumpa = budget(level)
    bonus = team_bonus(fighters) * (player_scale(level, player_level) if player_level else 1.0)
    return int(exp * (1 - KILL_SHARE) * bonus), int(wumpa * (1 - KILL_SHARE) * bonus)


def kill_pool(level, units, is_boss, fighters=1):
    """(exp, wumpa) pool of one kill, to be split between the players who fought it by damage. It grows with the
    number of fighters, so that each of them still earns what a lone player would, times the team bonus."""
    exp, wumpa = budget(level)
    share = KILL_SHARE * (BOSS_UNITS if is_boss else 1) / max(1, units)
    scale = share * max(1, fighters) * team_bonus(fighters)
    return max(1, int(exp * scale)), max(1, int(wumpa * scale))
