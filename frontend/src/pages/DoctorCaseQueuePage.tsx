import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { StatusPill } from "../components/StatusPill";
import { getDoctorCases, getErrorMessage } from "../lib/api";
import type { DoctorCasesResponse, TriageLevel, TriageQueueCase } from "../types";

const sections: Array<{ key: keyof DoctorCasesResponse; label: TriageLevel }> = [
  { key: "critical", label: "CRITICAL" },
  { key: "high", label: "HIGH" },
  { key: "medium", label: "MEDIUM" },
  { key: "low", label: "LOW" },
];

export function DoctorCaseQueuePage() {
  const [cases, setCases] = useState<DoctorCasesResponse>({
    critical: [],
    high: [],
    medium: [],
    low: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let intervalId: number | undefined;

    async function loadQueue() {
      try {
        const response = await getDoctorCases();
        if (!active) {
          return;
        }
        setCases(response);
        setError("");
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

    loadQueue();
    intervalId = window.setInterval(loadQueue, 10000);

    return () => {
      active = false;
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, []);

  return (
    <AppShell
      title="Doctor Case Queue"
      subtitle="Prioritized radiology cases grouped by urgency so the most critical studies surface first."
    >
      {loading ? <div className="panel empty-state">Loading doctor queue...</div> : null}
      {error ? <div className="alert alert-error">{error}</div> : null}

      <div className="queue-grid queue-grid--four">
        {sections.map((section) => {
          const items = cases[section.key] as TriageQueueCase[];
          return (
            <section className={`panel queue-section queue-section--${section.label.toLowerCase()}`} key={section.label}>
              <div className="panel-heading">
                <h2>{section.label}</h2>
                <p>{items.length} case(s)</p>
              </div>

              {items.length === 0 ? (
                <div className="empty-state">No {section.label.toLowerCase()} cases waiting for review.</div>
              ) : (
                items.map((item) => (
                  <article className="case-card" key={item.case_id}>
                    <div className="case-card__head">
                      <div>
                        <strong>{item.patient_name}</strong>
                        <p>{item.patient_token}</p>
                      </div>
                      <StatusPill kind="triage" value={item.triage_level} />
                    </div>

                    <dl className="key-value compact-key-value">
                      <div>
                        <dt>Prediction</dt>
                        <dd>{item.predicted_disease}</dd>
                      </div>
                      <div>
                        <dt>Confidence</dt>
                        <dd>{Math.round(item.confidence_score * 100)}%</dd>
                      </div>
                    </dl>

                    <Link className="button" to={`/doctor/case/${item.case_id}`}>
                      Review
                    </Link>
                  </article>
                ))
              )}
            </section>
          );
        })}
      </div>
    </AppShell>
  );
}
