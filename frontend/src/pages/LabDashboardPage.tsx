import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { StatusPill } from "../components/StatusPill";
import { getCase, getErrorMessage, getPatients } from "../lib/api";
import { loadRecentCaseIds, loadRegisteredPatients, replaceRegisteredPatients } from "../lib/storage";
import type { CaseDetail, PatientRegistrationResponse } from "../types";

export function LabDashboardPage() {
  const [recentCases, setRecentCases] = useState<CaseDetail[]>([]);
  const [registeredPatients, setRegisteredPatients] = useState<PatientRegistrationResponse[]>(() => loadRegisteredPatients());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadCases() {
      try {
        const ids = loadRecentCaseIds();
        const results = await Promise.allSettled(ids.map((caseId) => getCase(caseId)));
        if (!active) {
          return;
        }
        setRecentCases(
          results
            .filter((result): result is PromiseFulfilledResult<CaseDetail> => result.status === "fulfilled")
            .map((result) => result.value),
        );
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

    loadCases();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadPatients() {
      try {
        const patients = await getPatients();
        if (!active) {
          return;
        }
        setRegisteredPatients(patients);
        replaceRegisteredPatients(patients);
      } catch {
        if (!active) {
          return;
        }
      }
    }

    loadPatients();
    return () => {
      active = false;
    };
  }, []);

  const inFlightCount = recentCases.filter((item) => item.report_status === "UPLOADED").length;
  const doctorQueueCount = recentCases.filter((item) => item.report_status === "AWAITING_DOCTOR").length;
  const finalizedCount = recentCases.filter((item) => item.report_status === "FINALIZED").length;

  return (
    <AppShell
      title="Lab Intake Dashboard"
      subtitle="Register patients, launch report analysis, and track whether each upload has reached the doctor queue."
    >
      <section className="stats-grid">
        <article className="metric-card">
          <span>Registered patients</span>
          <strong>{registeredPatients.length}</strong>
        </article>
        <article className="metric-card">
          <span>Cases processing</span>
          <strong>{inFlightCount}</strong>
        </article>
        <article className="metric-card">
          <span>Awaiting doctor</span>
          <strong>{doctorQueueCount}</strong>
        </article>
        <article className="metric-card">
          <span>Finalized</span>
          <strong>{finalizedCount}</strong>
        </article>
      </section>

      <section className="grid grid--two">
        <article className="panel">
          <div className="panel-heading">
            <h2>Quick Actions</h2>
            <p>Follow the hospital intake sequence without leaving the dashboard.</p>
          </div>
          <div className="action-stack">
            <Link className="button" to="/lab/register">
              Register Patient
            </Link>
            <Link className="button button-secondary" to="/lab/upload">
              Upload Radiology Report
            </Link>
          </div>
          <p className="footer-note">
            New registrations generate a token that carries through upload, AI processing, and doctor review.
          </p>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <h2>Patient Tokens</h2>
            <p>Recent registrations available for immediate upload.</p>
          </div>
          <div className="stack-list">
            {registeredPatients.length === 0 ? (
              <div className="empty-state">No patients registered in this workstation session yet.</div>
            ) : (
              registeredPatients.map((patient) => (
                <div className="list-row" key={patient.patient_token}>
                  <div>
                    <strong>{patient.patient_name}</strong>
                    <p>
                      {patient.patient_token} · {patient.age} yrs · {patient.gender} · {patient.patient_type}
                    </p>
                  </div>
                  <Link className="button button-ghost" to={`/lab/upload?patientToken=${patient.patient_token}`}>
                    Upload
                  </Link>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Upload Status</h2>
          <p>Recent studies from this workstation and their current lifecycle state.</p>
        </div>
        {loading ? <div className="empty-state">Loading recent cases...</div> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}
        {!loading && !error && recentCases.length === 0 ? (
          <div className="empty-state">No uploaded cases are stored locally for this workstation yet.</div>
        ) : null}
        <div className="stack-list">
          {recentCases.map((item) => (
            <div className="list-row" key={item.case_id}>
              <div>
                <strong>{item.patient_name}</strong>
                <p>
                  {item.patient_token}
                  {item.predicted_disease ? ` · ${item.predicted_disease}` : ""}
                </p>
              </div>
              <div className="inline-cluster">
                {item.triage_level ? <StatusPill value={item.triage_level} kind="triage" /> : null}
                <StatusPill value={item.report_status} />
                <Link className="button button-ghost" to={`/lab/processing/${item.case_id}`}>
                  View
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
