import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { StatusPill } from "../components/StatusPill";
import { getCase, getErrorMessage, getTriageResult } from "../lib/api";
import type { CaseDetail, TriageResultSummary } from "../types";

const pipelineSteps = [
  "Save uploaded report",
  "Extract report text",
  "Run negation detection",
  "Clean findings text",
  "Run disease classification",
  "Calculate urgency score",
  "Store triage result",
];

export function TriageResultPage() {
  const { caseId = "" } = useParams();
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [triageResult, setTriageResult] = useState<TriageResultSummary | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let timerId: number | undefined;

    async function pollCase() {
      try {
        const detail = await getCase(caseId);
        if (!active) {
          return;
        }
        setCaseDetail(detail);

        if (
          detail.report_status === "AWAITING_DOCTOR" ||
          detail.report_status === "UNDER_REVIEW" ||
          detail.report_status === "FINALIZED"
        ) {
          const result = await getTriageResult(caseId);
          if (!active) {
            return;
          }
          setTriageResult(result);
        } else {
          setPollCount((value) => value + 1);
          timerId = window.setTimeout(pollCase, 2500);
        }
        setError("");
      } catch (requestError) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(requestError));
        timerId = window.setTimeout(pollCase, 3000);
      }
    }

    if (caseId) {
      pollCase();
    }

    return () => {
      active = false;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
  }, [caseId]);

  const processingComplete = Boolean(triageResult);
  const activeStep = processingComplete ? pipelineSteps.length - 1 : Math.min(pollCount, pipelineSteps.length - 1);

  return (
    <AppShell
      title="AI Triage Result"
      subtitle="The uploaded case moves through extraction, classification, urgency scoring, and explainability before it enters the doctor queue."
    >
      <section className="grid grid--two">
        <article className="panel">
          <div className="panel-heading">
            <h2>Pipeline Status</h2>
            <p>Realtime progression of the radiology triage engine.</p>
          </div>

          <div className="timeline">
            {pipelineSteps.map((step, index) => {
              const stepState = processingComplete || index < activeStep ? "complete" : index === activeStep ? "active" : "pending";
              return (
                <div className={`timeline-step timeline-step--${stepState}`} key={step}>
                  <div className="timeline-step__marker" />
                  <div>
                    <strong>{step}</strong>
                    <p>
                      {stepState === "complete"
                        ? "Completed"
                        : stepState === "active"
                          ? "In progress"
                          : "Waiting for previous step"}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel accent-panel">
          <div className="panel-heading">
            <h2>Triage Summary</h2>
            <p>Predicted disease, confidence score, urgency badge, and AI evidence.</p>
          </div>

          {error ? <div className="alert alert-error">{error}</div> : null}
          {!caseDetail && !error ? <div className="empty-state">Loading uploaded case...</div> : null}

          {caseDetail ? (
            <div className="stack-list">
              <div className="list-row">
                <div>
                  <strong>{caseDetail.patient_name}</strong>
                  <p>{caseDetail.patient_token}</p>
                </div>
                <StatusPill value={caseDetail.report_status} />
              </div>

              {triageResult ? (
                <>
                  <div className="list-row">
                    <span>Disease prediction</span>
                    <strong>{triageResult.disease_prediction}</strong>
                  </div>
                  <div className="list-row">
                    <span>Confidence score</span>
                    <strong>{Math.round(triageResult.confidence_score * 100)}%</strong>
                  </div>
                  <div className="list-row">
                    <span>Urgency</span>
                    <StatusPill kind="triage" value={triageResult.urgency_level} />
                  </div>

                  <div className="text-block">
                    <h3>Explainable AI Evidence</h3>
                    <p>{triageResult.explanation}</p>
                    {triageResult.evidence_words.length ? (
                      <div className="tag-list">
                        {triageResult.evidence_words.map((word) => (
                          <span className="tag" key={word}>
                            {word}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="text-block">
                    <h3>Detected Findings</h3>
                    <p>
                      Positive findings:{" "}
                      {triageResult.positive_findings.length
                        ? triageResult.positive_findings.join(", ")
                        : "None detected."}
                    </p>
                    <p>
                      Negated findings:{" "}
                      {triageResult.negated_findings.length
                        ? triageResult.negated_findings.join(", ")
                        : "None detected."}
                    </p>
                  </div>

                  <div className="alert alert-success">AI analysis complete. The case has been sent to the doctor queue.</div>
                </>
              ) : (
                <div className="empty-state">AI analysis running...</div>
              )}

              <div className="page-actions">
                <Link className="button button-ghost" to="/lab/dashboard">
                  Back to Dashboard
                </Link>
                {triageResult ? (
                  <Link className="button" to="/doctor/dashboard">
                    Open Doctor Queue
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}
        </article>
      </section>
    </AppShell>
  );
}
