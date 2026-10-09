# Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request, four jobs in parallel:

| Job | What it proves |
| --- | --- |
| **Tests** | every file compiles; the generated data files (`data/`) match their generators; the whole test suite passes |
| **Web app** | the frontend script parses; the web app tests (login links, cookies, public pages, Nostr endpoints) pass; the static export for Vercel builds |
| **Docker and compose** | `docker-compose.yml` is valid, the image builds, its libraries import for both the app user and root (the init step), `pg_dump` is there |
| **Upgrade rehearsal** | builds a database with the PREVIOUS release's own code, fills it with invented players, upgrades it with this commit (backup, migrations, Marvel launch) and runs `scripts/verify_launch.py`: nobody lost, everyone reset, podium paid, nothing else touched, equipment still resolves, a second start changes nothing |

## The same checks by hand

```bash
pip install -r requirements.txt -r requirements.dev.txt
python scripts/generate_badge_images.py          # badge pictures are not stored in git
python -m pytest tests --timeout=60 --timeout-method=signal -q
```

Against a copy of production (never against production itself):

```bash
python scripts/verify_launch.py --snapshot before.json     # on the copy, before the launch
MARVEL_LAUNCH=1 python scripts/init_stack.py               # the launch
python scripts/verify_launch.py --check before.json        # exit code 1 if anything is off
```

If the generated data is reported out of date, run `python scripts/marvel_roster.py --apply`,
`python scripts/marvel_dungeons.py --apply` and `python -m scripts.marvel_achievements`, then commit the result.
