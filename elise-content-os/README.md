# Development and Operations

Local setup and deployment notes for the Elise Verne Content OS application. See the [repository README](../README.md) for the system architecture, workflow, and engineering overview.

## Required knowledge inputs

The public repository currently includes only `data/seed/brand_voice.md`. Before running the seed or planner commands, provide the other inputs in one of the paths supported by `KnowledgeLoader`:

| Input | Preferred app path | Workspace fallback |
| --- | --- | --- |
| Character state | `data/seed/character_state.json` | `../character_state.json` |
| Monthly tracker | `data/seed/monthly_tracker.md` | `../monthly_tracker.md` |
| Scene JSON | `data/seed/scene_prompts.json` | `../elise_dataset/10_EliseVerneV1/elise_verne_prompts.json` |
| Scene text dataset | `data/seed/dataset/` | `../EliseVerneV1/dataset/` |

At least one scene source is required. Do not commit private datasets or production credentials merely to make local setup convenient.

## Local setup

```powershell
cd elise-content-os
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.cli seed
python -m app.cli trigger morning --dry-run
uvicorn app.main:app --reload
```

## Render deployment blueprint

- The root `render.yaml` defines the repository's web and cron deployment blueprint; an active production deployment is not verifiable from this repository alone.
- Set `DATABASE_URL` to the Neon pooled connection string.
- Set `DATABASE_URL_DIRECT` to the Neon direct connection string for migrations.
- Rotate/revoke any previously exposed OpenAI key before deploy.
- Keep `.env`, `.env.*`, local DB files, generated logs, and dataset image folders out of Git.
- Recovery: pause Render cron jobs first, roll back to the previous Render deploy, then restore/downgrade the DB only if the migration caused the incident.
- Neon connection split:
  - `DATABASE_URL`: pooled runtime connection for the web service and cron jobs.
  - `DATABASE_URL_DIRECT`: direct connection for `alembic upgrade head` and recovery work.
- Set Telegram webhook URL to:

```text
https://<your-render-domain>/telegram/webhook
```

Use `TELEGRAM_WEBHOOK_SECRET` as Telegram's `secret_token`.

## Production smoke checklist

```powershell
python -m app.cli seed
python -m app.cli openai-smoke
python -m app.cli trigger morning --dry-run
python -m app.cli analytics add --plan-id <plan_id> --content-format story --reach 0
```
