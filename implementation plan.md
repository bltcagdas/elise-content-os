# Elise Verne Content OS MVP - Implementation Plan

## Decisions
- App lives in `elise-content-os/`.
- Production data store is Neon Postgres.
- Runtime timezone is `Asia/Dubai`.
- Render cron schedules are UTC equivalents of Dubai-local content windows:
  - Morning: `03:00 UTC` for `07:00 Asia/Dubai`
  - Afternoon: `09:00 UTC` for `13:00 Asia/Dubai`
  - Evening: `15:30 UTC` for `19:30 Asia/Dubai`
- MVP keeps image generation and Instagram publishing manual.
- OpenAI model default is `gpt-5.4-mini`, configurable with `OPENAI_MODEL`.
- Regenerate exclusions persist in `content_plans.excluded_scene_ids`.

## Phase Status
| Phase | Scope | Status |
| --- | --- | --- |
| 0 | Secret hygiene, deploy exclusions, baseline docs | Done |
| 1 | FastAPI scaffold, config, DB, migrations | Done |
| 2 | 70-scene seed loader and monthly checklist seed | Done |
| 3 | Planner and regenerate exclusion chain | Done |
| 4 | OpenAI structured caption generation | Done |
| 5 | Telegram notification and callback loop | Done |
| 6 | Render/Neon deployment configuration | Done |
| 7 | Tests and smoke checks | Done |

## Acceptance Criteria
- `python -m app.cli seed` is idempotent.
- `python -m app.cli trigger morning --dry-run` creates a pending plan without calling OpenAI or Telegram.
- `/healthz` returns 200.
- Telegram webhook rejects requests without the configured secret token.
- Published callback increments the Dubai-local daily story counter once.
- Regenerate callback writes the current `scene_id` into `excluded_scene_ids` and the next plan cannot reuse it.

## Verification
- `compileall`: passed.
- `pytest`: 5 passed.
- `alembic upgrade head`: passed against local SQLite smoke DB.
- `python -m app.cli seed`: loaded 70 scenes and 8 monthly checklist items.
- `python -m app.cli trigger morning --dry-run`: returned Sunday skip, expected for Dubai-local silent day on the current run date.

## Operational Notes
- Rotate the previously exposed OpenAI key before any Git push or deployment.
- Use Neon pooled connection for app traffic and direct connection for Alembic migrations.
- Pause Render cron jobs during incident rollback to stop new content generation.
