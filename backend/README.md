# AI Radiology Triage & Decision Support Platform (Backend)

## Quickstart

1. Create a `.env` in `backend/`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/medicathon
HF_MODEL_NAME=distilbert-base-uncased
HF_ZERO_SHOT_MODEL=facebook/bart-large-mnli
HF_DEVICE=cpu
N8N_WEBHOOK_URL=http://localhost:5678/webhook/radion-case-finalized
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the API:

```bash
uvicorn main:app --reload
```

## Key Endpoints

- `POST /v1/reports/upload` (form-data: `text` or `file`)
- `POST /v1/reports/{report_id}/process`
- `GET /v1/reports/{report_id}`
- `GET /v1/dashboard/stats`

## Notes

- Use `database/schema.sql` to initialize Supabase/PostgreSQL tables.
- JSONB columns store model outputs for flexibility and auditing.
- n8n webhook automation can be configured with `N8N_WEBHOOK_URL`.
- Finalized case webhooks are documented in `../N8N_SETUP.md`.
