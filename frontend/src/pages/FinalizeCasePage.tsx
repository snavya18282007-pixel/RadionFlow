import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { StatusPill } from "../components/StatusPill";
import { useAuth } from "../context/AuthContext";
import { finalizeCase, getCase, getErrorMessage } from "../lib/api";
import type { CaseDetail } from "../types";

interface FinalizeLocationState {
  decision?: "APPROVE" | "OVERRIDE";
  finalDiagnosis?: string;
  doctorNotes?: string;
}

function dedupe(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

export function FinalizeCasePage() {
  const { caseId = "" } = useParams();
  const location = useLocation();
  const { auth } = useAuth();
  const draft = (location.state as FinalizeLocationState | null) ?? null;
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [decision, setDecision] = useState<"APPROVE" | "OVERRIDE">(draft?.decision ?? "APPROVE");
  const [finalDiagnosis, setFinalDiagnosis] = useState(draft?.finalDiagnosis ?? "");
  const [doctorNotes, setDoctorNotes] = useState(draft?.doctorNotes ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadCase() {
      try {
        const response = await getCase(caseId);
        if (!active) {
          return;
        }
        setCaseDetail(response);
        if (!draft?.finalDiagnosis) {
          setFinalDiagnosis(response.predicted_disease ?? "");
        }
      } catch (requestError) {
        if (active) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadCase();
    return () => {
      active = false;
    };
  }, [caseId, draft?.finalDiagnosis]);

  const diagnosisPreview =
    decision === "OVERRIDE" ? finalDiagnosis.trim() || "Doctor diagnosis required" : caseDetail?.predicted_disease ?? "Pending";
  const lifestylePreview = dedupe([
    ...(caseDetail?.analysis?.lifestyle.recommendations ?? []),
    ...(caseDetail?.analysis?.follow_up.recommendations ?? []),
  ]);

  async function handleFinalize() {
    if (!auth) {
      return;
    }
    if (decision === "OVERRIDE" && !finalDiagnosis.trim()) {
      setError("Provide the doctor diagnosis before finalizing an override.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const response = await finalizeCase(caseId, {
        doctor_name: auth.displayName,
        decision,
        final_diagnosis: decision === "OVERRIDE" ? finalDiagnosis.trim() : undefined,
        doctor_notes: doctorNotes.trim() || undefined,
      });
      setCaseDetail(response);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  const finalized = caseDetail?.report_status === "FINALIZED";

  return (
    <AppShell
      title="Finalize Report"
      subtitle="Confirm the doctor decision, generate patient-facing guidance, and trigger downstream automation."
    >
      {loading ? <div className="panel empty-state">Loading case...</div> : null}
      {error ? <div className="alert alert-error">{error}</div> : null}

      {caseDetail ? (
        <div className="review-grid">
          <section className="panel">
            <div className="panel-heading">
              <h2>Finalization Preview</h2>
              <p>Doctor decision, patient explanation, and care guidance before notification.</p>
            </div>

            <div className="inline-cluster">
              <StatusPill value={caseDetail.report_status} />
              {caseDetail.triage_level ? <StatusPill kind="triage" value={caseDetail.triage_level} /> : null}
            </div>

            {!finalized ? (
              <>
                <div className="decision-toggle">
                  <button
                    className={decision === "APPROVE" ? "decision-chip decision-chip--active" : "decision-chip"}
                    type="button"
                    onClick={() => setDecision("APPROVE")}
                  >
                    Approve AI diagnosis
                  </button>
                  <button
                    className={decision === "OVERRIDE" ? "decision-chip decision-chip--active" : "decision-chip"}
                    type="button"
                    onClick={() => setDecision("OVERRIDE")}
                  >
                    Override diagnosis
                  </button>
                </div>

                {decision === "OVERRIDE" ? (
                  <label className="field">
                    <span>Doctor Diagnosis</span>
                    <input value={finalDiagnosis} onChange={(event) => setFinalDiagnosis(event.target.value)} />
                  </label>
                ) : null}

                <label className="field">
                  <span>Doctor Notes</span>
                  <textarea rows={5} value={doctorNotes} onChange={(event) => setDoctorNotes(event.target.value)} />
                </label>
              </>
            ) : null}

            <div className="text-block">
              <h3>Diagnosis Heading</h3>
              <p>{finalized ? caseDetail.final_diagnosis : diagnosisPreview}</p>
            </div>

            <div className="text-block">
              <h3>Patient-Friendly Explanation</h3>
              <p>
                {finalized
                  ? caseDetail.patient_explanation
                  : `${caseDetail.patient_name}, your imaging has been reviewed and currently points to ${diagnosisPreview}. A doctor is confirming the result and the next steps for treatment and follow-up.`}
              </p>
            </div>

            <div className="text-block">
              <h3>Lifestyle Guidance</h3>
              <ul className="bullet-list">
                {(finalized ? caseDetail.lifestyle_guidance : lifestylePreview).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </section>

          <section className="panel accent-panel">
            <div className="panel-heading">
              <h2>Automation</h2>
              <p>n8n receives the finalized payload once the doctor confirms the case.</p>
            </div>

            <dl className="key-value">
              <div>
                <dt>Patient Token</dt>
                <dd>{caseDetail.patient_token}</dd>
              </div>
              <div>
                <dt>AI Prediction</dt>
                <dd>{caseDetail.predicted_disease}</dd>
              </div>
              <div>
                <dt>Review Decision</dt>
                <dd>{finalized ? caseDetail.review_decision : decision}</dd>
              </div>
              <div>
                <dt>Notification Status</dt>
                <dd>{String(caseDetail.automation_status.triggered ?? false)}</dd>
              </div>
            </dl>

            {caseDetail.automation_status.error ? (
              <div className="alert alert-warning">{String(caseDetail.automation_status.error)}</div>
            ) : null}

            <div className="page-actions">
              {!finalized ? (
                <button className="button" disabled={submitting} type="button" onClick={handleFinalize}>
                  {submitting ? "Finalizing..." : "Finalize and Notify"}
                </button>
              ) : null}
              <Link className="button button-ghost" to="/doctor/dashboard">
                Return to Queue
              </Link>
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
