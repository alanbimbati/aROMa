# Deploy su Raspberry (Docker Compose)

Tutta la configurazione sta in un file, `.env`. Poi un comando solo.

## Prima volta

```bash
cd ~/Bot/aroma
git pull
cp .env.example .env      # compila: BOT_TOKEN, DB_PASSWORD, WEBAPP_URL, WEBAPP_SECRET, NOSTR_NSEC...
docker compose up -d --build
```

Cosa succede, in ordine, senza altri comandi:

1. **postgres** parte (i dati restano nel volume `postgres_data`, non si perdono).
2. **init** (una volta per avvio, si ripete senza danni): backup se è in attesa il lancio Marvel, protezione dell'equipaggiamento
   dei giocatori, schema e migrazioni, lancio Marvel (solo se richiesto), immagini.
3. **aroma_bot** e **web** partono quando init ha finito. La web app risponde su `http://IP:8080`.

## Rendere la web app visibile a tutti

**Con ngrok (il modo più rapido):** crea un account su ngrok, copia l'authtoken e in `.env` metti
`COMPOSE_PROFILES=ngrok`, `NGROK_AUTHTOKEN=...` e lascia `WEBAPP_URL` vuoto: il bot legge da solo l'indirizzo dal tunnel
(sul piano gratuito cambia a ogni riavvio; con `NGROK_DOMAIN=il-tuo-dominio.ngrok-free.app` e lo stesso valore in
`WEBAPP_URL` resta fisso). Senza un indirizzo pubblico il bot non manda link.

`WEBAPP_URL` deve essere l'indirizzo pubblico. In alternativa, senza aprire porte sul router (Cloudflare):

1. Cloudflare Zero Trust > Networks > Tunnels > crea un tunnel, copia il token.
2. Nel tunnel aggiungi un hostname pubblico che punta a `http://web:8080`.
3. In `.env`: `COMPOSE_PROFILES=tunnel`, `CLOUDFLARE_TUNNEL_TOKEN=...`, `WEBAPP_URL=https://il-tuo-hostname`.
4. `docker compose up -d`.

(Se hai già un dominio con le porte aperte basta mettere il suo indirizzo in `WEBAPP_URL`.)
Il catalogo dei personaggi è pubblico; profilo e statistiche richiedono il link personale che manda il bot (`/web`).
Le immagini dei badge Nostr sono servite dalla stessa web app (`WEBAPP_URL/badges/...`).

## Lancio della stagione Marvel

1. In `.env` metti `MARVEL_LAUNCH=1`.
2. `docker compose up -d --build`.
3. Init fa un backup in `backups/pre_marvel_*.dump` (se il backup fallisce il lancio **non** parte), poi esegue il wipe una sola volta:
   viene ricordato nel database, quindi lasciare `MARVEL_LAUNCH=1` non lo ripete.

Per tornare indietro: `docker compose stop aroma_bot web`, poi
`docker compose exec -T postgres pg_restore -U $DB_USER -d $DB_NAME --clean --if-exists < backups/pre_marvel_XXXX.dump`.

## Token e impostazioni

`settings.py` non va più modificato a mano sul server: modalità, token e gruppo vengono da `.env`
(`BOT_TOKEN`, `GROUP_ID`; il compose imposta già `TEST=0`). Se sul Raspberry `settings.py` ha modifiche locali:
copia il token in `.env` e poi `git checkout settings.py`.

## Immagini Marvel

Alla prima accensione vengono scaricate (servizio gratuito Pollinations). Senza chiave sono circa una al minuto:
con `POLLINATIONS_API_KEY` (gratis, https://enter.pollinations.ai/keys) bastano pochi minuti. Quelle già presenti non si riscaricano.
