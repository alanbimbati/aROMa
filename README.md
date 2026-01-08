# Aroma Bot

Telegram bot per la gestione di punti, giochi e un sistema RPG completo.

## Migrazione al Branch RPG

**IMPORTANTE**: Se stai migrando dal branch `main` al branch `rpg`, devi eseguire lo script di migrazione del database prima di avviare il bot.

### Procedura di Migrazione

1. Assicurati di avere `points_official.db` (dal branch main) nella directory del progetto
2. Esegui lo script di migrazione:
   ```bash
   python3 migrate_from_main.py
   ```
3. Lo script creerà automaticamente backup di sicurezza
4. Avvia il bot normalmente:
   ```bash
   python3 main.py
   ```

### Cosa fa la Migrazione

Lo script di migrazione:
- ✅ Crea backup automatici dei database (`points_official_backup_*.db`)
- ✅ Migra tutti gli utenti esistenti
- ✅ Inizializza le statistiche RPG per ogni utente (salute: 100, mana: 50, danno base: 10)
- ✅ Preserva tutti i dati esistenti (exp, punti Wumpa, livello, premium, ecc.)
- ✅ Migra giochi, chiavi Steam, collezionabili e altri dati
- ✅ È idempotente (può essere eseguito più volte in sicurezza)

### Nuove Funzionalità RPG

Il branch RPG introduce:
- **Sistema di Combattimento PvE**: Mob giornalieri e raid boss
- **Personaggi**: Oltre 260 personaggi da sbloccare e equipaggiare
- **Statistiche RPG**: Salute, mana, danno, velocità, resistenza, critico
- **Abilità Speciali**: Ogni personaggio ha abilità uniche
- **Trasformazioni**: Sistema di trasformazioni per personaggi potenti
- **Sistema di Drop**: Oggetti, pozioni e collezionabili
- **Sfere del Drago**: Raccogli 7 sfere per esprimere desideri

## Installazione

1. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

2. Configura il token del bot in `config.ini`

3. Se stai migrando dal branch main, esegui la migrazione (vedi sopra)

4. Avvia il bot:
   ```bash
   python3 main.py
   ```

## Struttura del Progetto

- `main.py` - Entry point del bot
- `migrate_from_main.py` - Script di migrazione database
- `models/` - Modelli del database
- `services/` - Logica di business
- `data/` - File CSV con dati statici (personaggi, abilità, mob, ecc.)
- `images/` - Immagini dei personaggi e mob

## Configurazione

Il bot utilizza un file `config.ini` per la configurazione. Esempio:

```ini
[TELEGRAM]
token = YOUR_BOT_TOKEN

[GROUPS]
gruppo_aroma = -1001234567890
```

## Database

Il bot utilizza SQLite con due database principali:
- `points.db` - Database principale (branch RPG)
- `points_official.db` - Database del branch main (per migrazione)

## Supporto

Per problemi o domande, contatta gli amministratori del bot.
