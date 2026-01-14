CREATE TABLE points (
	id INTEGER NOT NULL, 
	numero INTEGER, 
	gruppo INTEGER, 
	nome VARCHAR(64), 
	PRIMARY KEY (id)
);
CREATE TABLE gruppo (
	id INTEGER NOT NULL, 
	nome VARCHAR(64), 
	link VARCHAR(64), 
	PRIMARY KEY (id)
);
CREATE TABLE utente (
	id INTEGER NOT NULL, 
	"id_Telegram" INTEGER, 
	nome VARCHAR(32), 
	cognome VARCHAR(32), 
	username VARCHAR(32), 
	exp INTEGER, 
	money INTEGER, 
	livello INTEGER, 
	vita INTEGER, 
	premium INTEGER, livello_selezionato String, start_tnt datetime, end_tnt datetime, scadenza_premium datetime, abbonamento_attivo integer, invincible_until TIMESTAMP, luck_boost INTEGER DEFAULT 0, health INTEGER DEFAULT 100, max_health INTEGER DEFAULT 100, current_hp INTEGER, mana INTEGER DEFAULT 50, max_mana INTEGER DEFAULT 50, base_damage INTEGER DEFAULT 10, stat_points INTEGER DEFAULT 0, last_health_restore TIMESTAMP, allocated_health INTEGER DEFAULT 0, allocated_mana INTEGER DEFAULT 0, allocated_damage INTEGER DEFAULT 0, allocated_speed INTEGER DEFAULT 0, allocated_resistance INTEGER DEFAULT 0, allocated_crit_rate INTEGER DEFAULT 0, last_stat_reset TIMESTAMP, last_attack_time TIMESTAMP, last_character_change TIMESTAMP, platform VARCHAR(50), game_name VARCHAR(100), active_status_effects TEXT, current_mana INTEGER DEFAULT 50, title TEXT, titles TEXT, 
	PRIMARY KEY (id), 
	UNIQUE ("id_Telegram"), 
	UNIQUE (username)
);
CREATE TABLE domenica (
	id INTEGER NOT NULL, 
	last_day DATE, 
	utente INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (utente)
);
CREATE TABLE steam (
	id INTEGER NOT NULL, 
	titolo VARCHAR(64), 
	titolone BOOLEAN, 
	preso_da VARCHAR(64), 
	steam_key VARCHAR(32), 
	PRIMARY KEY (id), 
	UNIQUE (steam_key)
);
CREATE TABLE nomigiochi (
	id INTEGER NOT NULL, 
	id_telegram INTEGER, 
	id_nintendo VARCHAR(256), 
	id_ps VARCHAR(256), 
	id_xbox VARCHAR(256), 
	id_steam VARCHAR(256), 
	PRIMARY KEY (id)
);
CREATE TABLE admin (
	id INTEGER NOT NULL, 
	id_telegram INTEGER, 
	PRIMARY KEY (id)
);
CREATE TABLE livello (
	id INTEGER NOT NULL, 
	livello INTEGER, 
	exp_to_lv INTEGER, 
	nome VARCHAR(32), 
	link_img VARCHAR(128), 
	saga VARCHAR(128), lv_premium integer, 
	PRIMARY KEY (id)
);
CREATE TABLE giocoaroma (
	id INTEGER NOT NULL, 
	nome VARCHAR, 
	descrizione VARCHAR, 
	link VARCHAR, 
	from_chat VARCHAR, 
	messageid INTEGER, 
	PRIMARY KEY (id)
);
CREATE TABLE giocoutente (
	id INTEGER NOT NULL, 
	"id_Telegram" INTEGER, 
	piattaforma VARCHAR, 
	nome VARCHAR, 
	PRIMARY KEY (id)
);
CREATE TABLE collezionabili (
	id INTEGER NOT NULL, 
	id_telegram VARCHAR NOT NULL, 
	oggetto VARCHAR NOT NULL, 
	data_acquisizione DATETIME NOT NULL, 
	quantita INTEGER NOT NULL, 
	data_utilizzo DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS "games" (
    id INTEGER NOT NULL, 
    title VARCHAR NOT NULL, 
    platform VARCHAR, 
    genre TEXT, 
    description TEXT, 
    language VARCHAR, 
    year INTEGER, 
    region VARCHAR, 
    message_link VARCHAR NOT NULL UNIQUE, premium integer,  -- Aggiunta del vincolo UNIQUE
    PRIMARY KEY (id)
);
CREATE TABLE character_ability (
	id INTEGER NOT NULL, 
	character_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	damage INTEGER, 
	mana_cost INTEGER, 
	elemental_type VARCHAR, 
	crit_chance INTEGER, 
	crit_multiplier FLOAT, 
	status_effect VARCHAR, 
	status_chance INTEGER, 
	status_duration INTEGER, 
	description VARCHAR, 
	PRIMARY KEY (id)
);
CREATE TABLE character_transformation (
	id INTEGER NOT NULL, 
	base_character_id INTEGER NOT NULL, 
	transformed_character_id INTEGER NOT NULL, 
	transformation_name VARCHAR NOT NULL, 
	wumpa_cost INTEGER NOT NULL, 
	duration_days FLOAT NOT NULL, 
	health_bonus INTEGER, 
	mana_bonus INTEGER, 
	damage_bonus INTEGER, 
	is_progressive BOOLEAN, 
	previous_transformation_id INTEGER, 
	required_level INTEGER, 
	PRIMARY KEY (id)
);
CREATE TABLE user_transformation (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	transformation_id INTEGER NOT NULL, 
	activated_at DATETIME, 
	expires_at DATETIME NOT NULL, 
	is_active BOOLEAN, 
	PRIMARY KEY (id)
);
CREATE TABLE user_character (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	character_id INTEGER NOT NULL, 
	obtained_at DATE, 
	PRIMARY KEY (id)
);
CREATE TABLE mob (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	health INTEGER NOT NULL, 
	max_health INTEGER NOT NULL, 
	spawn_time DATETIME, 
	is_dead BOOLEAN, 
	killer_id INTEGER, 
	reward_claimed BOOLEAN, 
	is_boss BOOLEAN, 
	image_path VARCHAR, 
	attack_type VARCHAR, 
	attack_damage INTEGER, 
	difficulty_tier INTEGER, 
	speed INTEGER, 
	mob_level INTEGER, 
	last_attack_time DATETIME, 
	description VARCHAR, 
	resistance INTEGER, passive_abilities TEXT, active_abilities TEXT, ai_behavior TEXT DEFAULT 'aggressive', phase_thresholds TEXT, current_phase INTEGER DEFAULT 1, active_buffs TEXT, 
	PRIMARY KEY (id)
);
CREATE TABLE raid (
	id INTEGER NOT NULL, 
	boss_name VARCHAR NOT NULL, 
	health INTEGER NOT NULL, 
	max_health INTEGER NOT NULL, 
	start_time DATETIME, 
	end_time DATETIME, 
	is_active BOOLEAN, 
	image_path VARCHAR, 
	attack_type VARCHAR, 
	attack_damage INTEGER, 
	description VARCHAR, 
	speed INTEGER, 
	PRIMARY KEY (id)
);
CREATE TABLE character_ownership (
	id INTEGER NOT NULL, 
	character_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	equipped_at DATETIME NOT NULL, 
	last_change_date DATE, 
	PRIMARY KEY (id)
);
CREATE TABLE raid_participation (
	id INTEGER NOT NULL, 
	raid_id INTEGER, 
	user_id INTEGER NOT NULL, 
	damage_dealt INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(raid_id) REFERENCES raid (id)
);
CREATE TABLE achievement (
	id INTEGER NOT NULL, 
	achievement_key VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	tier VARCHAR, 
	is_progressive BOOLEAN, 
	max_progress INTEGER, 
	trigger_event VARCHAR NOT NULL, 
	trigger_condition VARCHAR, 
	reward_points INTEGER, 
	reward_title VARCHAR, 
	cosmetic_reward VARCHAR, 
	icon VARCHAR, 
	hidden BOOLEAN, 
	flavor_text VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (achievement_key)
);
CREATE TABLE game_event (
	id INTEGER NOT NULL, 
	event_type VARCHAR NOT NULL, 
	user_id INTEGER, 
	event_data VARCHAR, 
	mob_id INTEGER, 
	combat_id INTEGER, 
	timestamp DATETIME, 
	processed_for_achievements BOOLEAN, 
	PRIMARY KEY (id)
);
CREATE TABLE mob_ability (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	ability_type VARCHAR NOT NULL, 
	damage INTEGER, 
	damage_type VARCHAR, 
	target_type VARCHAR, 
	max_targets INTEGER, 
	trigger_condition VARCHAR, 
	trigger_chance INTEGER, 
	status_effect VARCHAR, 
	status_duration INTEGER, 
	status_chance INTEGER, 
	buff_type VARCHAR, 
	buff_value INTEGER, 
	buff_duration INTEGER, 
	cooldown_turns INTEGER, 
	description VARCHAR, 
	flavor_text VARCHAR, 
	PRIMARY KEY (id)
);
CREATE TABLE combat_participation (
	id INTEGER NOT NULL, 
	mob_id INTEGER, 
	user_id INTEGER NOT NULL, 
	damage_dealt INTEGER, 
	hits_landed INTEGER, 
	critical_hits INTEGER, 
	healing_done INTEGER, 
	buffs_applied INTEGER, 
	exp_earned INTEGER, 
	loot_received VARCHAR, 
	reward_claimed BOOLEAN, 
	first_hit_time DATETIME, 
	last_hit_time DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(mob_id) REFERENCES mob (id)
);
CREATE TABLE user_achievement (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	achievement_id INTEGER, 
	current_progress INTEGER, 
	is_completed BOOLEAN, 
	completion_date DATETIME, 
	times_earned INTEGER, 
	last_progress_update DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(achievement_id) REFERENCES achievement (id)
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE season (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date DATETIME NOT NULL,
                end_date DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                exp_multiplier FLOAT DEFAULT 1.0,
                description TEXT,
                final_reward_name TEXT
            , theme VARCHAR);
CREATE TABLE season_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                season_id INTEGER,
                current_exp INTEGER DEFAULT 0,
                current_level INTEGER DEFAULT 1,
                has_premium_pass BOOLEAN DEFAULT 0,
                last_update DATETIME,
                FOREIGN KEY(season_id) REFERENCES season(id)
            );
CREATE TABLE season_reward (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER,
                level_required INTEGER NOT NULL,
                reward_type TEXT NOT NULL,
                reward_value TEXT NOT NULL,
                reward_name TEXT NOT NULL,
                is_premium BOOLEAN DEFAULT 0,
                icon TEXT,
                FOREIGN KEY(season_id) REFERENCES season(id)
            );
