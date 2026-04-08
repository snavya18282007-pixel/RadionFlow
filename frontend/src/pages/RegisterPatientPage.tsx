import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { getErrorMessage, registerPatient } from "../lib/api";
import { saveRegisteredPatient } from "../lib/storage";

export function RegisterPatientPage() {
  const navigate = useNavigate();
  const [patientName, setPatientName] = useState("");
  const [email, setEmail] = useState("");
  const [age, setAge] = useState("45");
  const [gender, setGender] = useState("Female");
  const [generatedToken, setGeneratedToken] = useState("");
  const [patientId, setPatientId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const response = await registerPatient({
        name: patientName,
        email,
        age: Number(age),
        gender,
      });
      saveRegisteredPatient(response);
      setGeneratedToken(response.token_number ?? response.patient_token);
      setPatientId(response.patient_id ?? "");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell
      title="Register Patient"
      subtitle="Capture core demographics, generate the hospital token, and pass that token straight into the upload workflow."
    >
      <section className="grid grid--two">
        <form className="panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <h2>Patient Intake</h2>
            <p>Minimal demographic capture for the lab technician workflow.</p>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>Name</span>
              <input required value={patientName} onChange={(event) => setPatientName(event.target.value)} />
            </label>
            <label className="field">
              <span>Email</span>
              <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label className="field">
              <span>Age</span>
              <input required min={0} max={120} type="number" value={age} onChange={(event) => setAge(event.target.value)} />
            </label>
            <label className="field">
              <span>Gender</span>
              <select value={gender} onChange={(event) => setGender(event.target.value)}>
                <option>Female</option>
                <option>Male</option>
                <option>Other</option>
              </select>
            </label>
          </div>

          {error ? <div className="alert alert-error">{error}</div> : null}

          <div className="page-actions">
            <button className="button" disabled={submitting} type="submit">
              {submitting ? "Generating Token..." : "Generate Token"}
            </button>
            <Link className="button button-ghost" to="/lab/dashboard">
              Back to Dashboard
            </Link>
          </div>
        </form>

        <aside className="panel accent-panel">
          <div className="panel-heading">
            <h2>Token Output</h2>
            <p>Token numbers become the primary identifier for intake, upload, and doctor queue tracking.</p>
          </div>

          {generatedToken ? (
            <div className="token-display">
              <span>Generated Token</span>
              <strong>{generatedToken}</strong>
              {patientId ? (
                <div className="list-row">
                  <span>Patient ID</span>
                  <strong>{patientId}</strong>
                </div>
              ) : null}
              <button
                className="button button-secondary"
                type="button"
                onClick={() => navigate(`/lab/upload?patientToken=${generatedToken}`)}
              >
                Continue to Upload
              </button>
            </div>
          ) : (
            <div className="empty-state">Submit the intake form to issue the next sequential hospital token.</div>
          )}
        </aside>
      </section>
    </AppShell>
  );
}
