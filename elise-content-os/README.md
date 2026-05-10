# Elise Verne Content OS

FastAPI service for the Elise Verne semi-automated content workflow.

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

## Production

- Deploy with the root `render.yaml`.
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
