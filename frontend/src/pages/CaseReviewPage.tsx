import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { StatusPill } from "../components/StatusPill";
import { useAuth } from "../context/AuthContext";
import { getCase, getErrorMessage, startReview } from "../lib/api";
import type { CaseDetail } from "../types";

type ReviewDecision = "APPROVE" | "OVERRIDE";

export function CaseReviewPage() {
  const { caseId = "" } = useParams();
  const { auth } = useAuth();
  const navigate = useNavigate();
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [decision, setDecision] = useState<ReviewDecision>("APPROVE");
  const [finalDiagnosis, setFinalDiagnosis] = useState("");
  const [doctorNotes, setDoctorNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadCase() {
      try {
        const detail = await getCase(caseId);
        const reviewDetail =
          detail.report_status === "AWAITING_DOCTOR" && auth
            ? await startReview(caseId, auth.displayName)
            : detail;

        if (!active) {
          return;
        }

        setCaseDetail(reviewDetail);
        setFinalDiagnosis(reviewDetail.predicted_disease ?? "");
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
  }, [auth, caseId]);

  const topTokens = Array.isArray(caseDetail?.analysis?.explainability.top_keywords)
    ? caseDetail.analysis.explainability.top_keywords
    : Array.isArray(caseDetail?.analysis?.explainability.model_insights.top_keywords)
      ? (caseDetail.analysis?.explainability.model_insights.top_keywords as string[])
    : [];
  const positiveFindings = caseDetail?.analysis?.findings.positive_findings ?? [];
  const negatedFindings = caseDetail?.analysis?.findings.negated_findings ?? [];

  return (
    <AppShell
      title="Case Review"
      subtitle="Inspect the original report, evaluate the AI rationale, and decide whether to approve or override the prediction."
    >
      {loading ? <div className="panel empty-state">Loading case...</div> : null}
      {error ? <div className="alert alert-error">{error}</div> : null}

      {caseDetail ? (
        <div className="review-grid">
          <section className="panel">
            <div className="panel-heading">
              <h2>Clinical Record</h2>
              <p>Original report and AI extraction context.</p>
            </div>

            <div className="inline-cluster">
              <StatusPill value={caseDetail.report_status} />
              {caseDetail.triage_level ? <StatusPill kind="triage" value={caseDetail.triage_level} /> : null}
            </div>

            <dl className="key-value">
              <div>
                <dt>Patient</dt>
                <dd>
                  {caseDetail.patient_name} · {caseDetail.patient_token}
                </dd>
              </div>
              <div>
                <dt>AI Prediction</dt>
                <dd>{caseDetail.predicted_disease ?? "Pending"}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{caseDetail.confidence_score ? `${Math.round(caseDetail.confidence_score * 100)}%` : "Pending"}</dd>
              </div>
            </dl>

            <div className="text-block">
              <h3>Original Report</h3>
              <p>{caseDetail.raw_text}</p>
            </div>

            <div className="text-block">
              <h3>Explainable AI Highlights</h3>
              <p>{caseDetail.analysis?.explainability.evidence.join(", ") || "No explicit evidence extracted."}</p>
              {topTokens.length ? (
                <div className="tag-list">
                  {topTokens.slice(0, 8).map((token) => (
                    <span className="tag" key={token}>
                      {token}
                    </span>
                  ))}
                </div>
              ) : null}
              <p>
                <strong>Positive findings:</strong>{" "}
                {positiveFindings.length ? positiveFindings.join(", ") : "None detected."}
              </p>
              <p>
                <strong>Negated findings:</strong>{" "}
                {negatedFindings.length ? negatedFindings.join(", ") : "None detected."}
              </p>
            </div>

            <div className={caseDetail.analysis?.inconsistencies.detected ? "alert alert-warning" : "alert alert-success"}>
              {caseDetail.analysis?.inconsistencies.detected
                ? caseDetail.analysis?.inconsistencies.reason || "Potential inconsistency detected."
                : "No report inconsistencies were flagged by the AI pipeline."}
            </div>
          </section>

          <section className="panel accent-panel">
            <div className="panel-heading">
              <h2>Doctor Action</h2>
              <p>Choose approval or override before moving into finalization.</p>
            </div>

            <div className="decision-toggle">
              <button
                className={decision === "APPROVE" ? "decision-chip decision-chip--active" : "decision-chip"}
                type="button"
                onClick={() => setDecision("APPROVE")}
              >
                Approve result
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
                <span>Final Diagnosis</span>
                <input value={finalDiagnosis} onChange={(event) => setFinalDiagnosis(event.target.value)} />
              </label>
            ) : null}

            <label className="field">
              <span>Clinical Notes</span>
              <textarea rows={6} value={doctorNotes} onChange={(event) => setDoctorNotes(event.target.value)} />
            </label>

            <div className="page-actions">
              <button
                className="button"
                type="button"
                onClick={() =>
                  navigate(`/doctor/finalize/${caseId}`, {
                    state: {
                      decision,
                      finalDiagnosis,
                      doctorNotes,
                    },
                  })
                }
              >
                Continue to Finalization
              </button>
              <Link className="button button-ghost" to="/doctor/dashboard">
                Back to Queue
              </Link>
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
