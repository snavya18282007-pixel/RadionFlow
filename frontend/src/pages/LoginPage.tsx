import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../services/api";
import { getDashboardPath, loginRoleOptions } from "../services/auth";

export function LoginPage() {
  const { auth, signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<(typeof loginRoleOptions)[number]["value"]>("lab_technician");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (auth) {
    return <Navigate to={getDashboardPath(auth.role)} replace />;
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (role === "admin") {
      setError("Admin login is not available in the current backend authentication service.");
      return;
    }

    setSubmitting(true);
    try {
      const nextAuth = await signIn({
        email,
        password,
        role,
      });
      navigate(getDashboardPath(nextAuth.role));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <header className="login-header">RADION AI</header>

      <div className="login-container">
        <div className="login-workstation">
          <section className="login-overview">
            <div className="login-overview__copy">
              <p className="login-kicker">Clinical Console</p>
              <h1>Radiology triage workspace for hospital teams.</h1>
              <p>
                Sign in to continue patient intake, AI-assisted report analysis, and prioritized clinical review in one
                structured workflow.
              </p>
            </div>

            <div className="login-workflow">
              <div className="workflow-line">
                <span className="workflow-line__step">Lab Technician</span>
                <strong>{"Register Patient -> Upload Report -> AI Processing"}</strong>
              </div>
              <div className="workflow-line">
                <span className="workflow-line__step">Doctor</span>
                <strong>{"Priority Queue -> Case Review -> Final Diagnosis"}</strong>
              </div>
              <div className="workflow-line">
                <span className="workflow-line__step">System</span>
                <strong>{"Findings -> Classification -> Triage -> Explainability -> Alerts"}</strong>
              </div>
            </div>
          </section>

          <section className="login-panel">
            <div className="login-panel__copy">
              <h2>Sign in to clinical console</h2>
              <p>Use your assigned hospital role to access the correct workspace.</p>
            </div>

            <form onSubmit={handleLogin} className="login-form">
              <Input label="Email">
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Input>

              <Input label="Password">
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Input>

              <Input label="Role">
                <select value={role} onChange={(e) => setRole(e.target.value as (typeof loginRoleOptions)[number]["value"])}>
                  {loginRoleOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </Input>

              {role === "admin" ? (
                <div className="login-note">
                  Admin is shown in the UI structure, but backend sign-in is currently enabled only for doctor and lab
                  technician roles.
                </div>
              ) : null}

              {error ? <div className="alert alert-error">{error}</div> : null}

              <Button type="submit" block disabled={submitting}>
                {submitting ? "Signing In..." : "Sign In"}
              </Button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
