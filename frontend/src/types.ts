export type UserRole = "doctor" | "lab_technician";

export type CaseStatus =
  | "UPLOADED"
  | "AI_ANALYZED"
  | "AWAITING_DOCTOR"
  | "UNDER_REVIEW"
  | "FINALIZED";

export type TriageLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface AuthState {
  token: string;
  role: UserRole;
  displayName: string;
  email: string;
}

export interface AuthLoginPayload {
  email: string;
  password: string;
  role: UserRole;
}

export interface AuthLoginResponse {
  token: string;
  role: UserRole;
  display_name: string;
  email: string;
}

export interface AuthRegisterPayload {
  email: string;
  password: string;
  role: UserRole;
  display_name?: string;
  access_code?: string;
}

export interface AuthRegisterResponse {
  id: string;
  email: string;
  role: UserRole;
  display_name?: string | null;
  created_at: string;
}

export interface PatientRegistrationPayload {
  name: string;
  email: string;
  age: number;
  gender: string;
}

export interface PatientRegistrationResponse {
  patient_id?: string | null;
  patient_token: string;
  token_number?: string | null;
  patient_name: string;
  name?: string | null;
  email?: string | null;
  age: number;
  gender: string;
  patient_type: string;
  created_at: string;
}

export interface UploadCaseResponse {
  case_id: string;
  report_id: string;
  patient_token: string;
  patient_name: string;
  report_status: CaseStatus;
  created_at: string;
  disease_prediction?: string | null;
  confidence_score?: number | null;
  urgency_level?: TriageLevel | null;
  explanation?: string | null;
}

export interface TriageQueueCase {
  case_id: string;
  patient_token: string;
  patient_name: string;
  predicted_disease: string;
  confidence_score: number;
  triage_level: TriageLevel;
  report_status: CaseStatus;
  created_at: string;
}

export interface DoctorCasesResponse {
  critical: TriageQueueCase[];
  high: TriageQueueCase[];
  medium: TriageQueueCase[];
  low: TriageQueueCase[];
}

export interface TriageResultSummary {
  report_id: string;
  disease_prediction: string;
  confidence_score: number;
  urgency_level: TriageLevel;
  explanation: string;
  evidence_words: string[];
  positive_findings: string[];
  negated_findings: string[];
  created_at: string;
}

export interface FindingsEntity {
  label: string;
  confidence: number;
  evidence?: string | null;
}

export interface ReportAnalysis {
  report_id: string;
  processed_at: string;
  findings: {
    entities: FindingsEntity[];
    summary: string;
    positive_findings: string[];
    negated_findings: string[];
  };
  classification: {
    disease: string;
    confidence: number;
    probabilities: Record<string, number>;
  };
  triage: {
    urgency_score: number;
    urgency_label: string;
    rationale: string;
  };
  explainability: {
    evidence: string[];
    top_keywords: string[];
    positive_findings: string[];
    negated_findings: string[];
    model_insights: Record<string, unknown>;
  };
  inconsistencies: {
    detected: boolean;
    reason?: string | null;
    details: string[];
  };
  lifestyle: {
    recommendations: string[];
  };
  follow_up: {
    recommendations: string[];
    timeframe_days: number;
  };
  notification: {
    triggered: boolean;
    channels: string[];
    message: string;
  };
}

export interface CaseDetail {
  case_id: string;
  patient_token: string;
  patient_name: string;
  patient_email?: string | null;
  patient_age?: number | null;
  patient_gender?: string | null;
  patient_type?: string | null;
  report_status: CaseStatus;
  triage_level?: TriageLevel | null;
  predicted_disease?: string | null;
  confidence_score?: number | null;
  doctor_name?: string | null;
  doctor_notes?: string | null;
  review_decision?: string | null;
  final_diagnosis?: string | null;
  patient_explanation?: string | null;
  lifestyle_guidance: string[];
  upload_metadata: Record<string, unknown>;
  automation_status: Record<string, unknown>;
  source_type: string;
  raw_text: string;
  created_at: string;
  finalized_at?: string | null;
  analysis?: ReportAnalysis | null;
}

export interface FinalizeCasePayload {
  doctor_name: string;
  decision: "APPROVE" | "OVERRIDE";
  final_diagnosis?: string;
  doctor_notes?: string;
}
