CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID,
    patient_token VARCHAR(32),
    file_url TEXT,
    modality VARCHAR(32),
    status VARCHAR(32) DEFAULT 'UPLOADED',
    source_type VARCHAR(20) NOT NULL,
    raw_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id UUID UNIQUE DEFAULT uuid_generate_v4(),
    token VARCHAR(32) PRIMARY KEY,
    token_number VARCHAR(32) UNIQUE,
    patient_name VARCHAR(120) NOT NULL,
    name VARCHAR(120),
    age INTEGER NOT NULL,
    gender VARCHAR(32) NOT NULL,
    patient_type VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('doctor', 'lab_technician')),
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL,
    findings JSONB NOT NULL,
    classification JSONB NOT NULL,
    triage JSONB NOT NULL,
    explainability JSONB NOT NULL,
    inconsistencies JSONB NOT NULL,
    lifestyle JSONB NOT NULL,
    follow_up JSONB NOT NULL,
    patient_explanation JSONB NOT NULL DEFAULT '{}'::jsonb,
    trend_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
    critical_alerts JSONB NOT NULL DEFAULT '{}'::jsonb,
    notification JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS triage_cases (
    report_id UUID PRIMARY KEY REFERENCES reports(id) ON DELETE CASCADE,
    patient_token VARCHAR(32) NOT NULL,
    patient_name VARCHAR(120) NOT NULL,
    patient_age INTEGER,
    patient_gender VARCHAR(32),
    patient_type VARCHAR(32),
    report_status VARCHAR(32) NOT NULL DEFAULT 'UPLOADED',
    predicted_disease VARCHAR(120),
    confidence_score DOUBLE PRECISION,
    triage_level VARCHAR(16),
    doctor_name VARCHAR(120),
    doctor_notes TEXT,
    review_decision VARCHAR(16),
    final_diagnosis VARCHAR(120),
    patient_explanation TEXT,
    lifestyle_guidance JSONB,
    upload_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    automation_status JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    finalized_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS triage_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    disease_prediction VARCHAR(120) NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    urgency_level VARCHAR(16) NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_report_results_report_id ON report_results(report_id);
CREATE INDEX IF NOT EXISTS idx_reports_patient_id ON reports(patient_id);
CREATE INDEX IF NOT EXISTS idx_reports_patient_token ON reports(patient_token);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_patients_id ON patients(id);
CREATE INDEX IF NOT EXISTS idx_patients_token_number ON patients(token_number);
CREATE INDEX IF NOT EXISTS idx_triage_cases_patient_token ON triage_cases(patient_token);
CREATE INDEX IF NOT EXISTS idx_triage_cases_status ON triage_cases(report_status);
CREATE INDEX IF NOT EXISTS idx_triage_cases_triage_level ON triage_cases(triage_level);
CREATE INDEX IF NOT EXISTS idx_triage_results_report_id ON triage_results(report_id);
CREATE INDEX IF NOT EXISTS idx_triage_results_urgency_level ON triage_results(urgency_level);
