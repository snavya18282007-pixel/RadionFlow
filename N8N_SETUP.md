# n8n Integration Setup

## What Is Integrated

The backend can send a webhook to n8n when a doctor finalizes a case.

The webhook is triggered from:

- `POST /cases/{case_id}/finalize`

The integration is implemented in:

- `backend/app/services/automation.py`
- `backend/app/services/case_management.py`

## Configure The Webhook URL

Create `backend/.env` from `backend/.env.example` and set:

```env
N8N_WEBHOOK_URL=https://radionai.app.n8n.cloud/webhook/radion-case-finalized
```

If `N8N_WEBHOOK_URL` is empty or missing, the backend will finalize the case normally but will report that automation was not triggered.

## Example n8n Flow

Suggested workflow:

1. `Webhook` node
2. `IF` node to branch on `triage_level` or `final_diagnosis`
3. Optional `Set` node to format the payload
4. Notification node such as:
   - Email
   - Slack
   - WhatsApp / Twilio
   - Google Sheets
   - Database insert

Recommended webhook path:

```text
/webhook/radion-case-finalized
```

## Payload Sent To n8n

The backend sends a focused JSON payload for email delivery with these top-level fields:

- `event`
- `source`
- `version`
- `case_id`
- `report_id`
- `patient_token`
- `to_email`
- `disease`
- `patient_explanation`
- `lifestyle_recommendations`
- `finalized_at`

## Example Payload

```json
{
  "event": "case.finalized",
  "source": "radion-ai-backend",
  "version": "1.0",
  "case_id": "8a8d8d40-0000-0000-0000-123456789abc",
  "report_id": "8a8d8d40-0000-0000-0000-123456789abc",
  "patient_token": "PT-1A2B3C4D",
  "to_email": "patient@example.com",
  "disease": "Pneumonia",
  "patient_explanation": {
    "text": "Your scan suggests pneumonia and your doctor has confirmed the finding."
  },
  "lifestyle_recommendations": [
    "Stay hydrated",
    "Follow the prescribed follow-up plan"
  ],
  "finalized_at": "2026-04-02T12:34:56.000000+00:00"
}
```

## What The UI Shows

After finalization, the frontend already shows:

- whether automation was triggered
- any automation error returned by the backend

The backend now also stores:

- `status_code` from the webhook response
- a short `response_preview` when available

## How To Test

1. Start n8n
2. Create a `Webhook` node with the path `radion-case-finalized`
3. Copy the production/test webhook URL
4. Set `N8N_WEBHOOK_URL` in `backend/.env`
5. Start the backend
6. Register a patient with an email address from the lab workflow
7. Finalize a case from the doctor workflow
8. Confirm the execution appears in n8n

## Notes

- The webhook is best-effort; a failure does not block case finalization.
- If the webhook fails, the error is stored in `automation_status`.
- This makes the clinical workflow resilient even if n8n is temporarily unavailable.
