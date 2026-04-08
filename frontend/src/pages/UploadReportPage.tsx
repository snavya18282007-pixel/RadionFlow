import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { getErrorMessage, getPatients, uploadReport } from "../lib/api";
import { loadRegisteredPatients, replaceRegisteredPatients, saveRecentCaseId } from "../lib/storage";
import type { PatientRegistrationResponse } from "../types";

export function UploadReportPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [patients, setPatients] = useState<PatientRegistrationResponse[]>(() => loadRegisteredPatients());
  const defaultPatientToken = searchParams.get("patientToken") ?? loadRegisteredPatients()[0]?.patient_token ?? "";
  const [patientToken, setPatientToken] = useState(defaultPatientToken);
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [xrayImage, setXrayImage] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadPatients() {
      try {
        const response = await getPatients();
        if (!active) {
          return;
        }
        setPatients(response);
        replaceRegisteredPatients(response);
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

  useEffect(() => {
    if (patients.length === 0) {
      return;
    }

    const matchingPatient = patients.find(
      (item) => item.patient_token === patientToken || item.token_number === patientToken,
    );
    if (matchingPatient) {
      if (matchingPatient.patient_token !== patientToken) {
        setPatientToken(matchingPatient.patient_token);
      }
      return;
    }

    const queryToken = searchParams.get("patientToken");
    if (queryToken && queryToken === patientToken) {
      setError("The selected token is no longer available. Choose a current registered patient before uploading.");
    }
    setPatientToken(patients[0]?.patient_token ?? "");
  }, [patientToken, patients, searchParams]);

  const selectedPatient =
    patients.find((item) => item.patient_token === patientToken || item.token_number === patientToken) ?? null;
  const reportFileType = reportFile?.type ?? "";
  const reportNeedsNotes = useMemo(
    () => reportFileType === "image/png" || reportFileType === "image/jpeg" || reportFileType === "image/jpg",
    [reportFileType],
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patientToken) {
      setError("Select a patient token before uploading.");
      return;
    }
    if (!reportFile) {
      setError("Attach the radiology report before continuing.");
      return;
    }
    if (reportNeedsNotes && !notes.trim()) {
      setError("Add notes when uploading PNG or JPG report scans so the AI pipeline has report text to analyze.");
      return;
    }

    setSubmitting(true);
    setError("");

    const formData = new FormData();
    formData.append("patient_token", patientToken);
    formData.append("report_file", reportFile);
    formData.append("modality", "XRAY");
    if (xrayImage) {
      formData.append("xray_image", xrayImage);
    }
    if (notes.trim()) {
      formData.append("notes", notes.trim());
    }

    try {
      const response = await uploadReport(formData);
      saveRecentCaseId(response.case_id);
      navigate(`/lab/processing/${response.case_id}`);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell
      title="Upload Radiology Report"
      subtitle="Attach the patient token, upload the diagnostic material, and push the case into the AI triage pipeline."
    >
      <section className="grid grid--two">
        <form className="panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <h2>Case Intake</h2>
            <p>Every upload is tied to a registered token before the AI triage engine starts processing.</p>
          </div>

          <div className="form-grid">
            <label className="field field--full">
              <span>Patient Token</span>
              <select
                value={patientToken}
                onChange={(event) => {
                  setPatientToken(event.target.value);
                  setError("");
                }}
              >
                <option value="">Select a registered patient</option>
                {patients.map((patient) => (
                  <option key={patient.patient_token} value={patient.patient_token}>
                    {patient.token_number ?? patient.patient_token} · {patient.name ?? patient.patient_name}
                  </option>
                ))}
              </select>
            </label>

            <div className="field field--full">
              <span>Radiology Report</span>
              <label
                className={`empty-state ${dragActive ? "ring-2 ring-[var(--primary)] ring-offset-2 ring-offset-[var(--bg)]" : ""}`}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setDragActive(true);
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setDragActive(false);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragActive(false);
                  const file = event.dataTransfer.files?.[0] ?? null;
                  if (!file) {
                    return;
                  }
                  setReportFile(file);
                }}
              >
                <div className="grid gap-2">
                  <strong>{reportFile ? reportFile.name : "Drag and drop PDF, PNG, or JPG report"}</strong>
                  <p>{reportFile ? `${Math.round(reportFile.size / 1024)} KB selected` : "Click to browse or drop the report here."}</p>
                  <input
                    accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                    required
                    type="file"
                    onChange={(event) => setReportFile(event.target.files?.[0] ?? null)}
                  />
                </div>
              </label>
            </div>

            <label className="field field--full">
              <span>Supporting X-ray Image</span>
              <input
                accept="image/png,image/jpeg,image/jpg"
                type="file"
                onChange={(event) => setXrayImage(event.target.files?.[0] ?? null)}
              />
            </label>

            <label className="field field--full">
              <span>{reportNeedsNotes ? "Required Notes for Image Report" : "Clinical Notes"}</span>
              <textarea
                rows={5}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Clinical context, symptoms, or report summary"
              />
            </label>
          </div>

          {error ? <div className="alert alert-error">{error}</div> : null}
          {!error && reportNeedsNotes ? (
            <div className="alert alert-warning">PNG and JPG reports are supported, but they require notes because OCR is not configured locally.</div>
          ) : null}

          <div className="page-actions">
            <button className="button" disabled={submitting} type="submit">
              {submitting ? "AI analysis running..." : "Upload and Start Triage"}
            </button>
            <Link className="button button-ghost" to="/lab/register">
              Register Another Patient
            </Link>
          </div>
        </form>

        <aside className="panel accent-panel">
          <div className="panel-heading">
            <h2>Selected Patient</h2>
            <p>Confirm token-based identity before the report enters the pipeline.</p>
          </div>

          {selectedPatient ? (
            <dl className="key-value">
              <div>
                <dt>Token</dt>
                <dd>{selectedPatient.token_number ?? selectedPatient.patient_token}</dd>
              </div>
              <div>
                <dt>Name</dt>
                <dd>{selectedPatient.name ?? selectedPatient.patient_name}</dd>
              </div>
              <div>
                <dt>Age</dt>
                <dd>{selectedPatient.age}</dd>
              </div>
              <div>
                <dt>Gender</dt>
                <dd>{selectedPatient.gender}</dd>
              </div>
              <div>
                <dt>Workflow</dt>
                <dd>AI analysis running after upload</dd>
              </div>
            </dl>
          ) : (
            <div className="empty-state">Choose a registered patient token to prepare this upload.</div>
          )}
        </aside>
      </section>
    </AppShell>
  );
}
