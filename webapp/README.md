# aROMa web app

A fast window on the game: character catalogue (search, filters, a full sheet per character), profile with titles,
stats, achievements by saga (with their Nostr badge state), season pass, dungeons, and the Nostr link.
It only reads game state, except the Nostr link, which it manages itself.

- **Run**: `python -m webapp` (port `WEBAPP_PORT`, default 8080). In Docker it is part of `docker compose up`.
- **Needs** the same database settings as the bot (`DB_*` in `.env`), plus `WEBAPP_URL` (the public address the
  login links point to) and `WEBAPP_SECRET` (signs the session cookie: without it sessions end on every restart).
- **Login**: the bot's `/web` command (or the 🌐 Web App button) sends a personal link, valid ten minutes and usable
  once; the browser trades it for a signed cookie that lasts a week. The catalogue is public, everything else needs it.
- **Nostr**: from the profile you link, change or unlink your npub. A one-time code is sent as a private Nostr message
  to that npub (the same flow as the bot's ⚡ Nostr button), so only its owner can link it. Needs `NOSTR_NSEC` on the server.
- **Pictures**: the bot's `images/` folder, scaled to WebP (128/256/512) on first request, cached in `cache/thumbs/`,
  at `/img/<name>/<width>.webp`. Badge pictures are public at `/badges/<achievement>-<tier>.png`.
- **Share links**: `/p/<id>` previews a character in chats (name, picture, attack) and opens the app on it.
- **Speed**: the whole catalogue (about 450 cards) is sent once, gzipped, and searched in the browser.

## Putting the public part on Vercel

Vercel runs functions and static files, not a server with a database, and it cannot reach a PostgreSQL on a home
network. What does not need the database can still live there (free, HTTPS, CDN, up when the Raspberry is off):
the catalogue, the character sheets, all the pictures, the badge images and the share pages. Everything personal
(`/api/me/*`, `/login`, season, dungeons, Nostr) is forwarded by Vercel to the real server, so the browser only ever
sees one address.

1. Make the real server reachable: the Cloudflare tunnel of `docker-compose.yml` (see `.env.example`) gives it a URL,
   say `https://api.example.org`.
2. Build the static site where the database is reachable:
   ```bash
   mkdir -p export
   docker compose run --rm -e EXPORT_DIR=/app/export -e API_ORIGIN=https://api.example.org \
       -e WEBAPP_URL=https://aroma.vercel.app web python -m webapp.export_static
   ```
3. Deploy it: `cd export && npx vercel --prod` (one login the first time).
4. Set `WEBAPP_URL=https://aroma.vercel.app` in `.env` so the bot's login links and the Nostr badge pictures use it,
   and `docker compose up -d`.

Rebuild and redeploy after changing characters, pictures or badges; the private API needs nothing, it is always live.
Without Vercel, the tunnel alone serves everything.

Endpoints: `/api/characters`, `/api/characters/{id}`, `/api/me`, `/api/me/characters`, `/api/me/stats`,
`/api/me/achievements`, `/api/me/nostr` (+ `start`, `confirm`, `unlink`), `/api/season`, `/api/dungeons`.

## Catalogo giochi (`#/giochi`)

Solo consultazione, dietro login: ricerca, filtri (piattaforma, genere, lingua, regione) e ordinamenti sul
catalogo degli album. I dati arrivano da un export della tabella `games` (solo colonne descrittive, niente link ai
messaggi) ripulito da `scripts/build_games_catalog.py` (piattaforme, generi, lingue, regioni e anni normalizzati,
duplicati uniti → `data/games_catalog.csv`). Le copertine le scarica `scripts/fetch_game_covers.py` dal database
pubblico dei thumbnail di libretro in `cache/game_covers/` (un gioco senza abbinamento sicuro non ha copertina:
meglio il segnaposto di una copertina sbagliata); riavviabile, ripete solo ciò che manca.
