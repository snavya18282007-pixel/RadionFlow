# Radion AI - Project Flow

## Overview
Radion AI is a clinical radiology triage platform built to simulate a real hospital workflow.

It includes:
- React + Vite frontend
- FastAPI backend
- Supabase PostgreSQL database
- AI-assisted radiology report analysis

The system is designed around role-based access and a workflow-first architecture:

`Login -> Lab Technician Workspace -> AI Processing -> Doctor Queue -> Review -> Final Diagnosis`

---

## Tech Stack

### Frontend
- React 18
- Vite
- TypeScript
- React Router
- Axios
- Tailwind CSS + custom CSS

### Backend
- FastAPI
- SQLAlchemy Async
- Pydantic v2
- Uvicorn

### Database
- Supabase PostgreSQL
- Local SQLite fallback for development startup safety

### AI / NLP
- TF-IDF + trained radiology classifier
- Rule-based radiology finding extraction
- medSpaCy negation detection
- spaCy clinical model (`en_core_sci_sm`) for report inconsistency analysis
- Severity-aware triage scoring
- Explainable AI keyword evidence

---

## Frontend Structure

```text
frontend/src
|
|-- components
|   |-- Header.tsx
|   |-- Sidebar.tsx
|   |-- PageLayout.tsx
|   |-- Input.tsx
|   |-- Button.tsx
|   |-- AppShell.tsx
|   |-- ProtectedRoute.tsx
|   `-- StatusPill.tsx
|
|-- pages
|   |-- LoginPage.tsx
|   |-- lab
|   |   |-- LabDashboard.tsx
|   |   |-- RegisterPatient.tsx
|   |   |-- UploadReport.tsx
|   |   `-- ProcessingStatus.tsx
|   `-- doctor
|       |-- DoctorQueue.tsx
|       |-- CaseReview.tsx
|       `-- FinalDiagnosis.tsx
|
|-- services
|   |-- api.ts
|   `-- auth.ts
|
|-- styles
|   `-- global.css
|
`-- App.tsx
```

---

## Final Frontend Workflow

### 1. Login
Users sign in from a clean clinical login page.

Supported roles:
- Lab Technician
- Doctor
- Admin option shown in UI

Note:
- Current backend authentication supports `doctor` and `lab_technician`
- `Admin` is present in UI structure, but is not an active backend-authenticated role unless explicitly enabled later

### 2. Lab Technician Workspace
Routes:
- `/lab/dashboard`
- `/lab/register`
- `/lab/upload`
- `/lab/processing/:caseId`

Flow:
1. Register patient
2. Generate token
3. Upload radiology report
4. AI processing status
5. Case enters doctor queue

### 3. Doctor Workspace
Routes:
- `/doctor/dashboard`
- `/doctor/case/:caseId`
- `/doctor/finalize/:caseId`

Flow:
1. Open doctor queue
2. Review prioritized cases
3. Inspect prediction, findings, evidence, inconsistencies
4. Approve or override
5. Finalize diagnosis

---

## Professional Layout System

Every workspace page now follows a structured enterprise layout:

```text
-------------------------------------------------
HEADER
-------------------------------------------------

SIDEBAR          |       MAIN CONTENT
                 |
Dashboard        |       Page Title
Register Patient |       ----------------
Upload Report    |       Clinical content
Doctor Queue     |
                 |
-------------------------------------------------
```

Design goals:
- workflow before decoration
- role separation
- fast navigation
- clinical readability
- no floating-card overload

---

## Backend Architecture

Main backend flow after upload:

```text
Upload Report
-> Extract Findings
-> Disease Classification
-> Urgency Triage
-> Explainable AI Evidence
-> Inconsistency Detection
-> Patient Explanation
-> Follow-up Recommendation
-> Disease Trend Analysis
-> Smart Critical Alerts
-> Persist Result
-> Doctor Queue
```

The pipeline runs automatically in the background after report upload.

---

## Backend Services

Located in:

`backend/app/services/`

Key services:
- `finding_extractor.py`
- `disease_classifier.py`
- `triage_engine.py`
- `explainability.py`
- `inconsistency.py`
- `patient_explainer.py`
- `followup.py`
- `disease_trend_analysis.py`
- `smart_critical_alerts.py`
- `report_pipeline.py`
- `case_management.py`

---

## Radiology Intelligence Pipeline

### 1. Finding Extraction
`finding_extractor.py`

Extracts structured radiology findings from report text using:
- rule-based matching
- model-assisted fallback extraction
- negation-aware text cleanup

Detects patterns like:
- pleural effusion
- consolidation
- pneumonia
- mass
- nodule
- fracture
- opacity
- tuberculosis
- pneumothorax

Returns structured data such as:
- findings
- positive findings
- negated findings
- body region
- severity terms

### 2. Disease Classification
`disease_classifier.py`

Predicts disease using:
- trained radiology classifier
- keyword-based clinical heuristics
- safety overrides for critical diseases

Possible outputs include:
- Normal
- Pneumonia
- Tuberculosis
- Pleural Effusion
- Lung Mass
- Fracture
- Cardiomegaly

### 3. Urgency Triage
`triage_engine.py`

Urgency is assigned using:
- predicted disease
- extracted findings
- severity terms
- model confidence

Priority levels:
- CRITICAL
- HIGH
- MEDIUM
- LOW

Critical escalation examples:
- pneumothorax
- severe consolidation
- large pleural effusion
- suspicious / spiculated mass

### 4. Explainable AI
`explainability.py`

Provides:
- evidence words
- top classifier keywords
- positive findings
- negated findings

### 5. Inconsistency Detection
`inconsistency.py`

Flags contradictory or clinically suspicious report text patterns for doctor review.

### 6. Patient Explanation
`patient_explainer.py`

Generates a patient-friendly summary from the AI result.

### 7. Follow-up Recommendation
`followup.py`

Generates disease-specific follow-up actions and timeframes.

### 8. Disease Trend Analysis
`disease_trend_analysis.py`

Uses historical `triage_results` data to compute:
- recent case volume
- previous window volume
- critical case count
- trend direction

### 9. Smart Critical Alerts
`smart_critical_alerts.py`

Builds structured critical alerts for:
- urgent review
- suspicious mass features
- report inconsistencies
- rising disease trends
- lower-confidence escalated cases

### 10. n8n Automation
`automation.py`

When a doctor finalizes a case, the backend can trigger an n8n webhook with:

- patient information
- report metadata
- predicted disease
- final diagnosis
- doctor notes
- patient explanation
- lifestyle guidance
- full analysis payload

The webhook is best-effort and does not block case finalization if n8n is unavailable.

---

## Database Flow

### Core tables
- `users`
- `patients`
- `reports`
- `report_results`
- `triage_cases`
- `triage_results`

### Result persistence
After processing, the backend stores:
- findings
- classification
- triage
- explainability
- inconsistency result
- lifestyle guidance
- follow-up guidance
- patient explanation
- trend analysis
- critical alerts
- notification metadata

---

## End-to-End Operational Flow

### Lab Technician
1. Login
2. Open dashboard
3. Register patient
4. System generates token
5. Upload report PDF / image + notes
6. Backend creates report + case
7. Background AI analysis starts
8. Processing page polls until result is available

### System
1. Extract findings
2. Remove negated findings
3. Predict disease
4. Calculate urgency
5. Build explainability evidence
6. Detect inconsistencies
7. Generate patient explanation
8. Generate follow-up recommendations
9. Compute disease trend summary
10. Build smart critical alerts
11. Persist result
12. Move case to doctor queue

### Doctor
1. Login
2. Open doctor queue
3. Review CRITICAL / HIGH / MEDIUM / LOW cases
4. Open case review
5. Check report, findings, evidence, inconsistencies
6. Approve or override
7. Finalize diagnosis
8. Generate final patient explanation + lifestyle guidance
9. Trigger automation payload
10. Optional n8n workflow sends downstream notifications / logging

---

## Key Routes

### Authentication
- `POST /auth/register`
- `POST /auth/login`

### Lab workflow
- `POST /patients/create`
- `GET /patients`
- `POST /reports/upload`

### Doctor workflow
- `GET /doctor/cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/review`
- `POST /cases/{case_id}/finalize`

### AI result access
- `GET /triage/result/{report_id}`
- `GET /triage-cases`
- `POST /analyze-report`

### Health
- `GET /health`
- `GET /health/db`

---

## Execution

### Backend
```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

### Open
- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

---

## Current Notes

- Backend is designed for Supabase PostgreSQL and includes compatibility migrations on startup.
- Local SQLite fallback is available in development if the remote database is temporarily unavailable.
- Admin UI structure exists, but backend role auth is currently limited to doctor and lab technician.
- `medSpaCy` is installed and active for negation-aware preprocessing, so phrases like `no evidence of pleural effusion` do not incorrectly raise disease predictions.
- The backend prefers the installed clinical spaCy model `en_core_sci_sm` for inconsistency analysis, with a lightweight keyword fallback only if model loading fails.
- The pipeline is modular and ready for further hospital-grade extensions such as OCR, PACS integration, and real alert delivery.
- n8n integration for finalized-case automation is available through `N8N_WEBHOOK_URL`.
- Setup details are documented in `N8N_SETUP.md`.
