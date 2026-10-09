"""Marvel roster: the 78 new characters, the rules that give every one its stats, and the writer.

Every number comes from the same formulas the first 56 Marvel characters already follow, so the
whole roster sits on one curve over levels 1-100:

    special damage 20 + 6L   mana cost 10 + 2L   speed 60 + L/2   price 200L   exp 50 L^2

An archetype shifts a character along trade-offs that cancel out (see ARCHETYPES and --report).

    python scripts/marvel_roster.py --report   # fairness figures, nothing written
    python scripts/marvel_roster.py --apply    # (re)write characters.csv and the Marvel abilities file
"""
import csv
import io
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_CSV = os.path.join(BASE_DIR, 'data', 'characters.csv')
ABILITIES_CSV = os.path.join(BASE_DIR, 'data', 'season2_marvel_abilities.csv')
REWARDS_CSV = os.path.join(BASE_DIR, 'data', 'season_marvel_rewards.csv')
FIRST_NEW_ID = 667
FIRST_ABILITY_ID = 1001

# Free (0): level-gated and always available. Shop (2): bought with Wumpa.
# Premium (1): only for premium accounts (Season Pass holders), never for sale.
FREE, PREMIUM, SHOP = 0, 1, 2

# dmg/mana multiply the level formula; speed and crit are added. The multipliers are picked so that
# expected damage per cast (dmg x crit expectation) stays within a few percent of 'balanced' and
# what an archetype gains it pays for in mana, speed or damage.
ARCHETYPES = {
    'balanced':  dict(dmg=1.00, mana=1.00, speed=0,  crit=0,  mult=1.5),
    'brawler':   dict(dmg=1.04, mana=1.06, speed=-4, crit=-1, mult=1.5),
    'speedster': dict(dmg=0.95, mana=1.00, speed=6,  crit=2,  mult=1.5),
    'marksman':  dict(dmg=0.95, mana=0.97, speed=0,  crit=5,  mult=1.7),
    'mage':      dict(dmg=1.00, mana=0.92, speed=-2, crit=0,  mult=1.5),
    'tank':      dict(dmg=0.93, mana=1.00, speed=-6, crit=0,  mult=1.5),
}

# Chance (%) and duration (turns) of each status the combat engine supports: the stronger
# the effect, the lower the chance, so no ability is simply better than another.
STATUS = {
    'stun': (15, 1), 'freeze': (15, 1), 'mind_control': (10, 2), 'confusion': (20, 2),
    'burn': (25, 3), 'poison': (25, 3), 'bleed': (25, 3), 'slow': (25, 2), 'weakness': (25, 2),
    'buff_attack': (30, 2), 'buff_defense': (30, 2),
}

# (art slug, name, level, archetype, team, alignment, status, special attack, description, tier, unique)
ROSTER = [
    ('kate_bishop', 'Kate Bishop', 12, 'marksman', 'Giovani Vendicatori', 'Good', 'bleed', 'Trick Arrow', "Arciera prodigio: non sbaglia una freccia, nemmeno quella con il trucco.", FREE, False),
    ('falcon', 'Falcon', 16, 'speedster', 'Avengers', 'Good', 'slow', 'Redwing Strike', "Sam Wilson plana sul campo di battaglia con le ali Stark e il fedele Redwing.", SHOP, False),
    ('echo', 'Echo', 19, 'balanced', 'Difensori', 'Good', 'weakness', 'Mimic Strike', "Maya Lopez copia ogni mossa che vede e la usa contro chi gliel'ha mostrata.", SHOP, False),
    ('wasp', 'Wasp', 21, 'speedster', 'Avengers', 'Good', 'stun', 'Wasp Sting', "Piccola e rapidissima, colpisce con scariche bioelettriche che paralizzano.", SHOP, False),
    ('ant_man', 'Ant-Man', 22, 'balanced', 'Avengers', 'Good', 'weakness', 'Pym Particle Punch', "Scott Lang cambia dimensione a piacere: un pugno minuscolo con il peso di un gigante.", FREE, False),
    ('vulture', 'Vulture', 23, 'speedster', 'Malvagi', 'Evil', 'bleed', 'Talon Dive', "Adrian Toomes piomba dall'alto con le sue ali di metallo affilato.", SHOP, False),
    ('yelena_belova', 'Yelena Belova', 24, 'marksman', 'S.H.I.E.L.D.', 'Neutral', 'bleed', "Widow's Bite", "Addestrata nella Stanza Rossa, è una Vedova Nera dal sarcasmo letale.", SHOP, False),
    ('daredevil', 'Daredevil', 25, 'brawler', 'Difensori', 'Good', 'stun', 'Billy Club Flurry', "Cieco ma non senza vista: il suo senso radar vede ogni colpo prima che arrivi.", SHOP, False),
    ('elektra', 'Elektra', 26, 'marksman', 'Difensori', 'Neutral', 'bleed', 'Sai Dance', "L'assassina più elegante di Hell's Kitchen danza tra i suoi sai.", SHOP, False),
    ('punisher', 'Punisher', 27, 'marksman', 'Difensori', 'Neutral', 'slow', 'Suppressing Fire', "Frank Castle non fa prigionieri: solo fuoco di copertura e giustizia sommaria.", SHOP, False),
    ('winter_soldier', 'Winter Soldier', 30, 'brawler', 'Avengers', 'Neutral', 'stun', 'Metal Fist Barrage', "Il braccio di metallo di Bucky Barnes colpisce come un maglio.", PREMIUM, False),
    ('blade', 'Blade', 31, 'brawler', 'Difensori', 'Neutral', 'bleed', 'Daywalker Slash', "Mezzo vampiro, cacciatore di vampiri: la sua lama argentata non perdona.", FREE, False),
    ('kitty_pryde', 'Kitty Pryde', 32, 'speedster', 'X-Men', 'Good', 'confusion', 'Phase Strike', "Attraversa muri e nemici: non si sa mai da dove colpirà.", SHOP, False),
    ('jubilee', 'Jubilee', 33, 'mage', 'X-Men', 'Good', 'burn', 'Plasmoid Burst', "Fuochi d'artificio mutanti, divertenti finché non ti esplodono addosso.", SHOP, False),
    ('nightcrawler', 'Nightcrawler', 34, 'speedster', 'X-Men', 'Good', 'confusion', 'Bamf Strike', "Teletrasporto in una nuvola di zolfo e un calcio da dove meno te lo aspetti.", SHOP, False),
    ('electro', 'Electro', 35, 'mage', 'Malvagi', 'Evil', 'stun', 'Chain Lightning', "Max Dillon scarica tutta l'energia di una centrale in un solo colpo.", SHOP, False),
    ('shang_chi', 'Shang-Chi', 36, 'brawler', 'Maestri di Kung Fu', 'Good', 'stun', 'Ten Rings Combo', "Il maestro delle Dieci Anelli unisce kung fu e magia antica.", PREMIUM, False),
    ('okoye', 'Okoye', 37, 'marksman', 'Wakanda', 'Good', 'bleed', 'Vibranium Spear', "Generale delle Dora Milaje: la lancia in vibranio non manca il bersaglio.", SHOP, False),
    ('mbaku', "M'Baku", 38, 'tank', 'Wakanda', 'Good', 'buff_defense', 'Gorilla Guard', "Il capo dei Jabari è un muro vivente che nessuno scalfisce.", SHOP, False),
    ('moon_knight', 'Moon Knight', 39, 'brawler', 'Difensori', 'Neutral', 'bleed', 'Crescent Darts', "Il pugile di Khonshu colpisce con la forza della luna crescente.", SHOP, False),
    ('x_23', 'X-23', 41, 'speedster', 'X-Men', 'Good', 'bleed', 'Adamantium Claws', "Laura Kinney: artigli di adamantio e istinto da predatrice.", FREE, False),
    ('cyclops', 'Cyclops', 42, 'marksman', 'X-Men', 'Good', 'burn', 'Optic Blast', "Scott Summers libera un raggio ottico che sfonda qualsiasi ostacolo.", SHOP, False),
    ('iceman', 'Iceman', 43, 'mage', 'X-Men', 'Good', 'freeze', 'Glacial Wave', "Bobby Drake congela il campo di battaglia, nemici compresi.", SHOP, False),
    ('rhino', 'Rhino', 44, 'tank', 'Malvagi', 'Evil', 'stun', 'Rhino Charge', "Una corazza di cheratina e una carica che non si ferma davanti a nulla.", SHOP, False),
    ('kraven', 'Kraven', 45, 'marksman', 'Malvagi', 'Evil', 'bleed', 'Great Hunt', "Il cacciatore supremo ha scelto la sua prossima preda: tu.", SHOP, False),
    ('domino', 'Domino', 46, 'marksman', 'X-Force', 'Neutral', 'weakness', 'Lucky Shot', "La fortuna è dalla sua parte: ogni proiettile trova la strada giusta.", SHOP, False),
    ('taskmaster', 'Taskmaster', 47, 'marksman', 'Malvagi', 'Evil', 'weakness', 'Photographic Reflexes', "Copia le mosse di chiunque dopo averle viste una volta sola.", SHOP, False),
    ('gamora', 'Gamora', 48, 'balanced', 'Guardiani', 'Good', 'bleed', 'Godslayer Slash', "La donna più pericolosa della galassia e la sua lama ammazzadei.", SHOP, False),
    ('storm', 'Storm', 49, 'mage', 'X-Men', 'Good', 'stun', 'Lightning Strike', "Ororo Munroe comanda tempeste e fulmini dal cielo.", PREMIUM, False),
    ('nebula', 'Nebula', 51, 'balanced', 'Guardiani', 'Neutral', 'weakness', 'Cybernetic Strike', "Una sorella ribelle, mezza macchina e interamente determinata.", FREE, False),
    ('drax', 'Drax', 52, 'brawler', 'Guardiani', 'Good', 'bleed', "Destroyer's Blades", "Il Distruttore non coglie le metafore, ma coglie benissimo i nemici.", SHOP, False),
    ('rocket_raccoon', 'Rocket Raccoon', 53, 'marksman', 'Guardiani', 'Good', 'burn', 'Big Gun Blast', "Piccolo, rabbioso e armato fino ai denti.", SHOP, False),
    ('mysterio', 'Mysterio', 54, 'mage', 'Malvagi', 'Evil', 'confusion', 'Illusion Storm', "Quentin Beck confonde chiunque con illusioni indistinguibili dal vero.", SHOP, False),
    ('sandman', 'Sandman', 55, 'tank', 'Malvagi', 'Evil', 'slow', 'Sand Prison', "Il corpo di sabbia di Flint Marko si rimodella e ti seppellisce.", SHOP, False),
    ('beast', 'Beast', 57, 'brawler', 'X-Men', 'Good', 'stun', 'Primal Pounce', "Hank McCoy: scienziato brillante e belva agilissima.", SHOP, False),
    ('psylocke', 'Psylocke', 58, 'speedster', 'X-Men', 'Good', 'bleed', 'Psychic Knife', "Una lama psichica che ferisce la mente prima del corpo.", PREMIUM, False),
    ('monica_rambeau', 'Monica Rambeau', 59, 'mage', 'Avengers', 'Good', 'burn', 'Photon Burst', "Capace di trasformarsi in pura energia elettromagnetica.", SHOP, False),
    ('colossus', 'Colossus', 60, 'tank', 'X-Men', 'Good', 'buff_defense', 'Organic Steel', "Piotr Rasputin: pelle d'acciaio e un cuore d'oro.", SHOP, False),
    ('mantis', 'Mantis', 61, 'mage', 'Guardiani', 'Good', 'confusion', 'Empathic Wave', "Sente e manipola le emozioni di chiunque la circondi.", SHOP, False),
    ('nick_fury', 'Nick Fury', 62, 'marksman', 'S.H.I.E.L.D.', 'Good', 'weakness', 'Helicarrier Barrage', "Il direttore dello S.H.I.E.L.D. ha sempre un piano, e una portaerei volante.", FREE, False),
    ('vision', 'Vision', 63, 'mage', 'Avengers', 'Good', 'burn', 'Solar Beam', "Un sintezoide che assorbe energia solare e la restituisce in un raggio.", PREMIUM, False),
    ('war_machine', 'War Machine', 64, 'marksman', 'Avengers', 'Good', 'burn', 'Ultimate Arsenal', "James Rhodes e un arsenale che non finisce mai le munizioni.", SHOP, False),
    ('lizard', 'Lizard', 65, 'brawler', 'Malvagi', 'Evil', 'poison', 'Reptile Venom', "Il dottor Connors, divorato dal suo stesso siero rettiliano.", SHOP, False),
    ('rogue', 'Rogue', 66, 'brawler', 'X-Men', 'Good', 'weakness', 'Power Drain', "Un tocco e ti ruba forza, poteri e ricordi.", SHOP, False),
    ('she_hulk', 'She-Hulk', 67, 'brawler', 'Avengers', 'Good', 'stun', 'Gamma Slam', "Avvocato di giorno, gigante di giada a tempo pieno.", SHOP, False),
    ('quicksilver', 'Quicksilver', 68, 'speedster', 'X-Men', 'Neutral', 'confusion', 'Sonic Rush', "Pietro Maximoff corre così veloce che gli avversari colpiscono la sua scia.", SHOP, False),
    ('human_torch', 'Human Torch', 69, 'mage', 'Fantastic Four', 'Good', 'burn', 'Flame On!', "Johnny Storm si trasforma in una torcia vivente.", SHOP, False),
    ('invisible_woman', 'Invisible Woman', 69, 'mage', 'Fantastic Four', 'Good', 'buff_defense', 'Force Field', "Sue Storm: scudi e invisibilità, il cuore dei Fantastici Quattro.", SHOP, False),
    ('shuri', 'Shuri', 70, 'balanced', 'Wakanda', 'Good', 'stun', 'Vibranium Gauntlet', "La mente più brillante del Wakanda e un guanto che fa saltare i sistemi.", SHOP, False),
    ('ms_marvel', 'Ms. Marvel', 70, 'balanced', 'Avengers', 'Good', 'stun', 'Embiggen Fist', "Kamala Khan allunga le braccia e fa partire un pugno gigantesco.", SHOP, False),
    ('iron_man', 'Iron Man', 75, 'balanced', 'Avengers', 'Good', 'burn', 'Mark 85 Nanotech Barrage', "L'ultima armatura di Tony Stark: nanotecnologia che si riforma a ogni colpo.", SHOP, False),
    ('fantastic_four', 'Fantastic Four', 85, 'balanced', 'Fantastic Four', 'Good', 'buff_attack', 'Fantastic Combo', "La prima famiglia Marvel colpisce tutta insieme: elasticità, fuoco, forza e scudo.", SHOP, False),
    ('green_goblin', 'Green Goblin', 71, 'balanced', 'Malvagi', 'Evil', 'burn', 'Pumpkin Bomb', "Norman Osborn ride, e le sue zucche esplodono.", SHOP, False),
    ('mr_fantastic', 'Mr. Fantastic', 72, 'balanced', 'Fantastic Four', 'Good', 'slow', 'Stretch Bind', "Reed Richards si allunga, ti avvolge e ti rallenta.", FREE, False),
    ('thing', 'Thing', 73, 'tank', 'Fantastic Four', 'Good', 'stun', "It's Clobberin' Time", "Ben Grimm: roccia arancione e un pugno che scuote il terreno.", SHOP, False),
    ('mystique', 'Mystique', 74, 'speedster', 'Malvagi', 'Evil', 'confusion', 'Shapeshift Strike', "Può essere chiunque, anche il tuo compagno di squadra.", SHOP, False),
    ('morbius', 'Morbius', 75, 'brawler', 'Malvagi', 'Neutral', 'weakness', 'Blood Fury', "Lo scienziato vampiro che lotta contro la propria sete.", SHOP, False),
    ('wiccan', 'Wiccan', 76, 'mage', 'Giovani Vendicatori', 'Good', 'confusion', 'Reality Hex', "Billy Kaplan piega la realtà con un incantesimo di caos.", SHOP, False),
    ('speed', 'Speed', 77, 'speedster', 'Giovani Vendicatori', 'Good', 'confusion', 'Lightning Dash', "Tommy Shepherd corre, colpisce e sparisce prima che tu batta ciglio.", SHOP, False),
    ('nova', 'Nova', 78, 'balanced', 'Cosmici', 'Good', 'burn', 'Nova Force', "Il Centurione Richard Rider incanala la Nova Force in una cometa di fuoco.", PREMIUM, False),
    ('kingpin', 'Kingpin', 80, 'tank', 'Malvagi', 'Evil', 'stun', 'Crushing Grip', "Wilson Fisk governa il crimine di New York con una mano sola.", SHOP, False),
    ('cable', 'Cable', 80, 'marksman', 'X-Force', 'Neutral', 'bleed', 'Temporal Rifle', "Viaggiatore del tempo con un fucile che sa dove sarai.", SHOP, False),
    ('doc_ock', 'Doc Ock', 81, 'balanced', 'Malvagi', 'Evil', 'slow', 'Tentacle Barrage', "Otto Octavius: quattro tentacoli di metallo e una mente geniale.", FREE, False),
    ('baron_zemo', 'Baron Zemo', 82, 'marksman', 'Malvagi', 'Evil', 'weakness', "Masters' Strike", "Un maestro stratega che smonta i nemici prima ancora di combatterli.", SHOP, False),
    ('agatha_harkness', 'Agatha Harkness', 83, 'mage', 'Maghi', 'Neutral', 'mind_control', 'Witch Curse', "La strega più antica di Westview: ogni maledizione ha il suo prezzo.", SHOP, False),
    ('america_chavez', 'America Chavez', 84, 'brawler', 'Giovani Vendicatori', 'Good', 'stun', 'Star Portal Kick', "Calcia portali tra le dimensioni, e tra i denti di chi li merita.", PREMIUM, False),
    ('ghost_rider', 'Ghost Rider', 85, 'brawler', 'Difensori', 'Neutral', 'burn', 'Penance Stare', "Lo Spirito della Vendetta ti guarda e ti fa pagare ogni colpa.", PREMIUM, False),
    ('carnage', 'Carnage', 86, 'brawler', 'Malvagi', 'Evil', 'bleed', 'Symbiote Frenzy', "Il simbionte rosso è puro caos in forma liquida.", SHOP, False),
    ('blue_marvel', 'Blue Marvel', 87, 'balanced', 'Avengers', 'Good', 'weakness', 'Anti-Matter Burst', "Adam Brashear controlla l'antimateria con la calma di un fisico.", SHOP, False),
    ('emma_frost', 'Emma Frost', 92, 'mage', 'X-Men', 'Neutral', 'mind_control', 'Diamond Mind', "Telepata di classe e di diamante: non c'è mente che non possa spezzare.", PREMIUM, False),
    ('namor', 'Namor', 89, 'brawler', 'Cosmici', 'Neutral', 'stun', 'Trident Tsunami', "Il re di Atlantide scatena l'oceano con un colpo di tridente.", PREMIUM, False),
    ('professor_x', 'Professor X', 91, 'mage', 'X-Men', 'Good', 'mind_control', 'Cerebro Command', "Charles Xavier: la mente più potente del pianeta, ora a tuo servizio.", PREMIUM, True),
    ('photon', 'Photon', 92, 'mage', 'Avengers', 'Good', 'burn', 'Photon Nova', "Monica Rambeau alla massima potenza: pura luce.", SHOP, False),
    ('magneto', 'Magneto', 94, 'mage', 'X-Men', 'Neutral', 'stun', 'Magnetic Crush', "Il Padrone del Magnetismo piega ogni metallo alla sua volontà.", PREMIUM, True),
    ('kang', 'Kang', 95, 'mage', 'Malvagi', 'Evil', 'slow', 'Chrono Strike', "Il Conquistatore sa già come finisce, e tu non vinci.", PREMIUM, True),
    ('adam_warlock', 'Adam Warlock', 96, 'mage', 'Cosmici', 'Good', 'burn', 'Soul Gem Blast', "Il Guerriero Cosmico brandisce la Gemma dell'Anima.", PREMIUM, True),
    ('sentry', 'Sentry', 98, 'brawler', 'Avengers', 'Neutral', 'weakness', 'Void Surge', "Ha la forza di mille soli, e il Vuoto con sé.", PREMIUM, True),
    ('jean_grey', 'Jean Grey', 99, 'mage', 'X-Men', 'Good', 'burn', 'Phoenix Rising', "La Fenice Nera rinasce dalle sue stesse ceneri.", PREMIUM, True),
]

# The original 56: kept as they are, but sorted into the teams and the free/shop/premium scheme.
EXISTING_TEAMS = {
    'Stan Lee': 'Leggende', 'Peter Parker': 'Spider-Verse', 'Spider-Man': 'Spider-Verse', 'Iron Spider': 'Spider-Verse',
    'Cosmic Spider-Man': 'Spider-Verse', 'Tony Stark': 'Avengers', 'Iron Man Mark 1': 'Avengers',
    'Iron Man Hulkbuster': 'Avengers', 'Iron Man Bleeding Edge': 'Avengers', 'Steve Rogers': 'Avengers',
    'Captain America': 'Avengers', 'Captain America (Worth)': 'Avengers', 'Bruce Banner': 'Avengers',
    'Hulk': 'Avengers', 'World Breaker Hulk': 'Avengers', 'Thor Odinson': 'Asgard', 'Thor': 'Asgard',
    'King Thor': 'Asgard', 'Rune King Thor': 'Asgard', 'Natasha Romanoff': 'Avengers', 'Black Widow': 'Avengers',
    'Clint Barton': 'Avengers', 'Hawkeye': 'Avengers', 'Ronin': 'Avengers', 'Stephen Strange': 'Maghi',
    'Doctor Strange': 'Maghi', 'Sorcerer Supreme': 'Maghi', 'Wanda Maximoff': 'Avengers', 'Scarlet Witch': 'Avengers',
    'Scarlet Witch (Darkhold)': 'Avengers', 'Carol Danvers': 'Cosmici', 'Captain Marvel': 'Cosmici',
    'Binary Form': 'Cosmici', "T'Challa": 'Wakanda', 'Black Panther': 'Wakanda', 'King of the Dead': 'Wakanda',
    'Groot (Baby)': 'Guardiani', 'Groot': 'Guardiani', 'King Groot': 'Guardiani', 'Peter Quill': 'Guardiani',
    'Star-Lord': 'Guardiani', 'Logan (Weapon X)': 'X-Men', 'Wolverine': 'X-Men', 'Old Man Logan': 'X-Men',
    'Wade Wilson': 'X-Force', 'Deadpool': 'X-Force', 'Eddie Brock': 'Simbionti', 'Venom': 'Simbionti',
    'King in Black Venom': 'Simbionti', 'Teschio Rosso': 'Malvagi', 'Loki': 'Asgard', 'Ultron': 'Malvagi',
    'Thanos': 'Cosmici', "Thanos (Guanto dell'Infinito)": 'Cosmici', 'Silver Surfer': 'Cosmici', 'Galactus': 'Cosmici',
}

HEADER = ['id', 'nome', 'livello', 'lv_premium', 'exp_required', 'special_attack_name', 'special_attack_damage',
          'special_attack_mana_cost', 'price', 'description', 'character_group', 'max_concurrent_owners', 'is_pokemon',
          'elemental_type', 'subgroup', 'alignment', 'crit_chance', 'crit_multiplier', 'required_character_id', 'speed',
          'is_transformation', 'base_character_id', 'transformation_mana_cost', 'transformation_duration_days',
          'bonus_health', 'bonus_mana', 'bonus_damage', 'bonus_resistance', 'bonus_crit', 'bonus_speed',
          'special_attack_gif']
# Photon is the top form of Monica Rambeau, like the Spider-Man and Iron Man chains
TRANSFORMATIONS = {'Photon': 'Monica Rambeau', 'Iron Man': 'Iron Man Bleeding Edge'}


def stats(level, archetype):
    a = ARCHETYPES[archetype]
    return dict(
        damage=round((20 + 6 * level) * a['dmg']),
        mana=round((10 + 2 * level) * a['mana']),
        speed=60 + level // 2 + a['speed'],
        crit=5 + a['crit'],
        mult=a['mult'],
    )


def expected_damage(level, archetype):
    s = stats(level, archetype)
    return s['damage'] * (1 + s['crit'] / 100 * (s['mult'] - 1))


def build_rows(rows):
    """New characters as CSV rows, ids assigned from FIRST_NEW_ID by level."""
    by_name = {r['nome']: r for r in rows}
    ids = {}
    out = []
    ordered = sorted(ROSTER, key=lambda e: (e[2], e[1]))
    for offset, e in enumerate(ordered):
        ids[e[1]] = FIRST_NEW_ID + offset
    # Every character is held by one player at a time, a hero and its forms counting as one
    for slug, name, level, arch, team, align, status, special, desc, tier, unique in ordered:
        s = stats(level, arch)
        transformation = name in TRANSFORMATIONS
        base_id = ids.get(TRANSFORMATIONS.get(name)) or (by_name[TRANSFORMATIONS[name]]['id'] if transformation else '')
        out.append({
            'id': ids[name], 'nome': name, 'livello': level, 'lv_premium': tier, 'exp_required': 50 * level * level,
            'special_attack_name': special, 'special_attack_damage': s['damage'], 'special_attack_mana_cost': s['mana'],
            'price': 200 * level if tier == SHOP else 0, 'description': desc, 'character_group': 'Marvel',
            'max_concurrent_owners': 1, 'is_pokemon': 0, 'elemental_type': 'Normal',
            'subgroup': team, 'alignment': align, 'crit_chance': s['crit'], 'crit_multiplier': s['mult'],
            'required_character_id': base_id, 'speed': s['speed'], 'is_transformation': 1 if transformation else 0,
            'base_character_id': base_id, 'transformation_mana_cost': 50 if transformation else '',
            'transformation_duration_days': 2 if transformation else '',
            'bonus_health': 5 * level if transformation else 0, 'bonus_mana': 2 * level if transformation else 0,
            'bonus_damage': 3 * level if transformation else 0, 'bonus_resistance': 2 * level if transformation else 0,
            'bonus_crit': 2 if transformation else 0, 'bonus_speed': 2 if transformation else 0, 'special_attack_gif': '',
        })
    meta = {e[1]: e for e in ROSTER}
    return out, ids, meta


def ability_rows(characters, status_by_name):
    """One ability per Marvel character, the one its special attack uses in combat."""
    rows = []
    for offset, c in enumerate(sorted(characters, key=lambda r: int(r['id']))):
        status = status_by_name.get(c['nome'], 'buff_attack')
        chance, duration = STATUS[status]
        rows.append({
            'id': FIRST_ABILITY_ID + offset, 'character_id': c['id'], 'name': c['special_attack_name'],
            'damage': c['special_attack_damage'], 'mana_cost': c['special_attack_mana_cost'],
            'elemental_type': 'Normal', 'crit_chance': c['crit_chance'], 'crit_multiplier': c['crit_multiplier'],
            'status_effect': status, 'status_chance': chance, 'status_duration': duration,
            'description': f"Usa {c['special_attack_name']}.",
        })
    return rows


# What the original 56 do on top of their damage (named after what each of them is known for)
EXISTING_STATUS = {
    'Stan Lee': 'buff_attack', 'Peter Parker': 'slow', 'Spider-Man': 'slow', 'Iron Spider': 'weakness',
    'Cosmic Spider-Man': 'stun', 'Tony Stark': 'burn', 'Iron Man Mark 1': 'burn', 'Iron Man Hulkbuster': 'stun',
    'Iron Man Bleeding Edge': 'burn', 'Steve Rogers': 'buff_defense', 'Captain America': 'buff_defense',
    'Captain America (Worth)': 'stun', 'Bruce Banner': 'weakness', 'Hulk': 'stun', 'World Breaker Hulk': 'stun',
    'Thor Odinson': 'stun', 'Thor': 'stun', 'King Thor': 'stun', 'Rune King Thor': 'burn', 'Natasha Romanoff': 'bleed',
    'Black Widow': 'stun', 'Clint Barton': 'bleed', 'Hawkeye': 'bleed', 'Ronin': 'bleed', 'Stephen Strange': 'confusion',
    'Doctor Strange': 'mind_control', 'Sorcerer Supreme': 'mind_control', 'Wanda Maximoff': 'confusion',
    'Scarlet Witch': 'confusion', 'Scarlet Witch (Darkhold)': 'mind_control', 'Carol Danvers': 'burn',
    'Captain Marvel': 'burn', 'Binary Form': 'burn', "T'Challa": 'bleed', 'Black Panther': 'bleed',
    'King of the Dead': 'weakness', 'Groot (Baby)': 'buff_defense', 'Groot': 'buff_defense', 'King Groot': 'buff_defense',
    'Peter Quill': 'burn', 'Star-Lord': 'burn', 'Logan (Weapon X)': 'bleed', 'Wolverine': 'bleed', 'Old Man Logan': 'bleed',
    'Wade Wilson': 'confusion', 'Deadpool': 'confusion', 'Eddie Brock': 'poison', 'Venom': 'poison',
    'King in Black Venom': 'poison', 'Teschio Rosso': 'weakness', 'Loki': 'confusion', 'Ultron': 'burn',
    'Thanos': 'stun', "Thanos (Guanto dell'Infinito)": 'stun', 'Silver Surfer': 'freeze', 'Galactus': 'weakness',
}


def load_characters():
    raw = open(CHARACTERS_CSV, newline='', encoding='utf-8').read()
    return list(csv.DictReader(io.StringIO(raw, newline='')))


def regenerate():
    """Returns (all character rows, abilities) with the Marvel part rebuilt from scratch."""
    rows = [r for r in load_characters() if not (r['character_group'] == 'Marvel' and int(r['id']) >= FIRST_NEW_ID)]
    for r in rows:
        if r['character_group'] != 'Marvel':
            continue
        r['subgroup'] = EXISTING_TEAMS[r['nome']]
        r['max_concurrent_owners'] = '1'
        if r['nome'] == 'Stan Lee':
            # Everyone starts as him: the only shared character
            r['lv_premium'], r['price'], r['max_concurrent_owners'] = FREE, 0, '-1'
        elif r['lv_premium'] == '1' and r['nome'] not in ('Teschio Rosso', 'Loki', 'Ultron', 'Silver Surfer', 'Thanos', 'Galactus'):
            r['lv_premium'] = SHOP  # the starter heroes: bought, then they grow into their forms
        elif r['lv_premium'] == '1':
            r['price'] = 0  # premium elite: not for sale
    new_rows, ids, meta = build_rows(rows)
    all_rows = rows + [{k: str(v) for k, v in n.items()} for n in new_rows]
    status = dict(EXISTING_STATUS)
    status.update({e[1]: e[6] for e in ROSTER})
    marvel = [r for r in all_rows if r['character_group'] == 'Marvel']
    return all_rows, ability_rows(marvel, status)



# Season Pass: one reward per rank on each track. The free track is generous, the premium track pays
# 2.7x the Wumpa and adds characters the shop would charge for; the last rank is the headline prize.
PASS_RANKS = 30
FREE_CHARACTERS = {5: 'Falcon', 10: 'Daredevil', 15: 'Kitty Pryde', 20: 'Cyclops', 25: 'Rocket Raccoon', 30: 'Human Torch'}
PREMIUM_CHARACTERS = {4: 'Echo', 8: 'Punisher', 12: 'Nightcrawler', 16: 'Okoye', 20: 'Gamora', 24: 'War Machine', 28: 'Thing', 30: 'Iron Man'}
FREE_WUMPA, PREMIUM_WUMPA = 150, 400  # per rank
REWARD_HEADER = ['level_required', 'is_premium', 'reward_type', 'reward_value', 'reward_name', 'icon']


def pass_rewards(all_rows):
    ids = {r['nome']: r['id'] for r in all_rows if r['character_group'] == 'Marvel'}
    rows = []
    for rank in range(1, PASS_RANKS + 1):
        for premium, wumpa, characters in ((0, FREE_WUMPA, FREE_CHARACTERS), (1, PREMIUM_WUMPA, PREMIUM_CHARACTERS)):
            amount = wumpa * rank
            rows.append({'level_required': rank, 'is_premium': premium, 'reward_type': 'points', 'reward_value': amount,
                         'reward_name': f"{amount} Wumpa", 'icon': '💰'})
            if rank in characters:
                name = characters[rank]
                rows.append({'level_required': rank, 'is_premium': premium, 'reward_type': 'character',
                             'reward_value': ids[name], 'reward_name': name, 'icon': '🦸'})
    return rows


def write_csv(path, rows, header):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=header, lineterminator='\r\n')
    writer.writeheader()
    writer.writerows(rows)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        f.write(out.getvalue())


def report(all_rows):
    marvel = [r for r in all_rows if r['character_group'] == 'Marvel']
    print(f"{len(marvel)} Marvel characters ({len(ROSTER)} new)")
    deciles = {}
    tiers = {}
    for r in marvel:
        d = (int(r['livello']) - 1) // 10
        deciles[d] = deciles.get(d, 0) + 1
        tiers.setdefault(d, {0: 0, 1: 0, 2: 0})[int(r['lv_premium'])] += 1
    for d in sorted(deciles):
        t = tiers[d]
        print(f"  lv {d*10+1:3}-{d*10+10:3}: {deciles[d]:3} characters  (free {t[0]}, premium {t[1]}, shop {t[2]})")
    print("Fairness (expected damage per cast vs the balanced build of the same level, mana vs balanced):")
    for arch in ARCHETYPES:
        ratios = [expected_damage(l, arch) / expected_damage(l, 'balanced') for l in range(10, 101, 10)]
        manas = [stats(l, arch)['mana'] / stats(l, 'balanced')['mana'] for l in range(10, 101, 10)]
        s = stats(50, arch)
        print(f"  {arch:9} damage x{min(ratios):.2f}-{max(ratios):.2f}  mana x{min(manas):.2f}-{max(manas):.2f}  speed {s['speed']:+d} vs {stats(50,'balanced')['speed']}  crit {s['crit']}% x{s['mult']}")


if __name__ == '__main__':
    all_rows, abilities = regenerate()
    levels = [e[2] for e in ROSTER]
    assert len({e[1] for e in ROSTER}) == len(ROSTER), "duplicate names"
    assert all(1 <= l <= 100 for l in levels)
    report(all_rows)
    if '--apply' in sys.argv:
        write_csv(CHARACTERS_CSV, all_rows, HEADER)
        write_csv(ABILITIES_CSV, abilities, list(abilities[0].keys()))
        write_csv(REWARDS_CSV, pass_rewards(all_rows), REWARD_HEADER)
        print(f"Wrote {CHARACTERS_CSV}, {ABILITIES_CSV} and {REWARDS_CSV}")
    else:
        print("(dry run: pass --apply to write)")
