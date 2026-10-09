"""Marvel achievements, written to the season pack file the manifest points at.

Dungeon goals are tied to the dungeon's id, which follows the ladder in marvel_dungeons.py, so this file is
generated from it: rerun it after changing the ladder.

    python scripts/marvel_achievements.py
"""
import csv
import json
import os

from scripts.marvel_dungeons import dungeon_ids

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE_DIR, 'data', 'season2_marvel_achievements.csv')
RANKS = ('bronze', 'silver', 'gold')


def tiers(thresholds, exp, titles):
    return {r: {"threshold": n, "rewards": {"exp": e, "title": t}} for r, n, e, t in zip(RANKS, thresholds, exp, titles)}


# (key, name, description, stat, thresholds, exp, titles). A dungeon goal names the dungeon instead of a stat.
KILLS = (1, 10, 50)
RUNS = (1, 5, 15)
SPEC = [
    ('street_hero', '🏙️ Eroe di Quartiere', 'Completa Strade di New York.', ('dungeon', 'Strade di New York'), RUNS, (100, 300, 700), ("Amico del Vicinato", "Eroe di Quartiere", "Protettore di New York")),
    ('vulture_clipped', '🦅 Ali Tarpate', "Sconfiggi l'Avvoltoio.", 'kill_vulture', KILLS, (100, 300, 700), ("Tarpa Ali", "Cacciatore di Avvoltoi", "Signore dei Cieli")),
    ('hells_kitchen', '🥷 Ombra di Hell\'s Kitchen', "Completa Hell's Kitchen.", ('dungeon', "Hell's Kitchen"), RUNS, (200, 600, 1200), ("Guardiano della Notte", "Nemico della Mano", "Diavolo Custode")),
    ('rhino_charge', '🦏 Fermare il Rinoceronte', 'Sconfiggi Rhino.', 'kill_rhino', KILLS, (200, 600, 1200), ("Ferma-Carica", "Domatore di Rinoceronti", "Corna Spezzate")),
    ('hydra_infiltrator', '🐙 Infiltrato Hydra', 'Completa il dungeon Base Hydra.', ('dungeon', 'Base Hydra'), RUNS, (300, 800, 1500), ("Agente sotto copertura", "Infiltrato", "Nemico dell'Hydra")),
    ('hydra_soldier_hunter', '🪖 Taglia Soldati', 'Sconfiggi i Soldati Hydra.', 'kill_soldato_hydra', (25, 100, 400), (300, 800, 1500), ("Recluta Ribelle", "Spezza Ranghi", "Flagello dell'Hydra")),
    ('red_skull_slayer', '💀 Teschio Rosso', 'Sconfiggi il Teschio Rosso.', 'kill_teschio_rosso', KILLS, (300, 800, 1500), ("Sfidante del Teschio", "Nemesi del Teschio", "Fine del Teschio Rosso")),
    ('oscorp_survivor', '🎃 Sopravvissuto a Oscorp', 'Completa Torre Oscorp.', ('dungeon', 'Torre Oscorp'), RUNS, (400, 1000, 1800), ("Visitatore di Oscorp", "Esperto di Laboratori", "Incubo di Norman")),
    ('goblin_pumpkins', '🎃 Zucche Esplosive', 'Sconfiggi Green Goblin.', 'kill_green_goblin', KILLS, (400, 1000, 1800), ("Schiva-Zucche", "Disinnesca Bombe", "Re del Carnevale")),
    ('great_hunt', '🏹 La Preda Diventa Cacciatore', 'Completa La Grande Caccia.', ('dungeon', 'La Grande Caccia'), RUNS, (500, 1200, 2200), ("Preda Sfuggente", "Cacciatore di Cacciatori", "Re della Giungla")),
    ('kraven_trophy', '🦁 Il Trofeo di Kraven', 'Sconfiggi Kraven.', 'kill_kraven', KILLS, (500, 1200, 2200), ("Preda Inattesa", "Trofeo Vivente", "Fine della Caccia")),
    ('galaxy_guardian', '🚀 Guardiano della Galassia', 'Completa il dungeon Guardiani della Galassia.', ('dungeon', 'Guardiani della Galassia'), RUNS, (300, 800, 1500), ("Reietto Stellare", "Guardiano", "Leggenda della Galassia")),
    ('symbiote_outbreak', '🕷️ Focolaio Simbionte', 'Completa Invasione Simbionte.', ('dungeon', 'Invasione Simbionte'), RUNS, (600, 1500, 2600), ("Immune al Simbionte", "Contenitore di Focolai", "Cura Vivente")),
    ('carnage_chaos', '🩸 Nessuna Strage', 'Sconfiggi Carnage.', 'kill_carnage', KILLS, (600, 1500, 2600), ("Argine al Caos", "Fermacarneficina", "Fine del Caos")),
    ('asgard_guest', '⚡ Ospite di Asgard', 'Completa il dungeon Famiglia Divina (Asgard).', ('dungeon', 'Famiglia Divina (Asgard)'), RUNS, (300, 800, 1500), ("Ospite di Asgard", "Campione di Asgard", "Figlio di Odino")),
    ('loki_trickster', "🎭 Dio dell'Inganno", 'Sconfiggi Loki.', 'kill_loki', KILLS, (300, 800, 1500), ("Smaschera Inganni", "Burlato e Burlatore", "Gloriosa Vittoria")),
    ('chitauri_invasion', '👽 Invasione Chitauri', 'Respingi i Chitauri.', 'kill_chitauri', (50, 250, 1000), (300, 800, 1500), ("Difensore di New York", "Muro Contro l'Invasione", "Salvatore della Terra")),
    ('ultron_no_strings', '🤖 Nessuna Stringa', 'Sconfiggi Ultron.', 'kill_ultron', KILLS, (300, 800, 1500), ("Spegni Robot", "Antivirus Vivente", "Era dell'Uomo")),
    ('mutant_world', '🧲 Mondo Mutante', 'Completa Mondo Mutante.', ('dungeon', 'Mondo Mutante'), RUNS, (700, 1800, 3000), ("Alleato dei Mutanti", "Scudo dei Mutanti", "Custode dell'X-Gene")),
    ('magneto_pole', '🧲 Polo Opposto', 'Sconfiggi Magneto.', 'kill_magneto', KILLS, (700, 1800, 3000), ("Resistente al Magnetismo", "Polo Opposto", "Spezza-Acciaio")),
    ('conqueror_end', '⏳ Il Finale Riscritto', 'Completa Il Conquistatore.', ('dungeon', 'Il Conquistatore'), RUNS, (800, 2000, 3400), ("Viaggiatore Ribelle", "Riscrivi-Tempo", "Padrone del Destino")),
    ('kang_defeated', '🕰️ Kang Sconfitto', 'Sconfiggi Kang.', 'kill_kang', KILLS, (800, 2000, 3400), ("Rovina il Piano", "Spezza-Cronologie", "Fine del Conquistatore")),
    ('infinity_war', "💎 Guerra dell'Infinito", 'Completa il dungeon Infinity War.', ('dungeon', 'Infinity War'), RUNS, (800, 2000, 3400), ("Sopravvissuto", "Resistente all'Infinito", "Ultima Linea")),
    ('thanos_inevitable', '🧤 Ineluttabile', 'Sconfiggi Thanos.', 'kill_thanos', KILLS, (800, 2000, 3400), ("Sfida l'Ineluttabile", "Ineluttabile Anche Tu", "Titano Caduto")),
    ('avengers_assemble', '🛡️ Avengers, Assemble!', 'Completa il dungeon Endgame.', ('dungeon', 'Endgame'), RUNS, (1000, 2500, 4000), ("Vendicatore", "Vendicatore Supremo", "Il Più Potente Eroe")),
    ('galactus_devourer', '🌌 Divoratore di Mondi', "Completa il dungeon L'Arrivo di Galactus.", ('dungeon', "L'Arrivo di Galactus"), (1, 3, 10), (1500, 3500, 6000), ("Sfamatore Cosmico", "Placa-Fame", "Salvatore dei Mondi")),
]


def build():
    ids = dungeon_ids()
    rows = []
    for key, name, desc, stat, thresholds, exp, titles in SPEC:
        stat_key = f"dungeon_def_{ids[stat[1]]}_completed" if isinstance(stat, tuple) else stat
        rows.append([key, name, desc, stat_key, 'marvel', json.dumps(tiers(thresholds, exp, titles), ensure_ascii=False)])
    return rows


if __name__ == '__main__':
    rows = build()
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['key', 'name', 'description', 'stat_key', 'category', 'tiers'])
        w.writerows(rows)
    print(f"{len(rows)} Marvel achievements written to {OUT}")
