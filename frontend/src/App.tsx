import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import { LoginPage } from "./pages/LoginPage";
import { CaseReview } from "./pages/doctor/CaseReview";
import { DoctorQueue } from "./pages/doctor/DoctorQueue";
import { FinalDiagnosis } from "./pages/doctor/FinalDiagnosis";
import { LabDashboard } from "./pages/lab/LabDashboard";
import { ProcessingStatus } from "./pages/lab/ProcessingStatus";
import { RegisterPatient } from "./pages/lab/RegisterPatient";
import { UploadReport } from "./pages/lab/UploadReport";
import { getDashboardPath } from "./services/auth";

function RoleRedirect() {
  const { auth } = useAuth();

  if (!auth) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getDashboardPath(auth.role)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RoleRedirect />} />
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute allowedRole="lab_technician" />}>
        <Route path="/lab/dashboard" element={<LabDashboard />} />
        <Route path="/lab/register" element={<RegisterPatient />} />
        <Route path="/lab/upload" element={<UploadReport />} />
        <Route path="/lab/processing/:caseId" element={<ProcessingStatus />} />
        <Route path="/lab/result/:caseId" element={<ProcessingStatus />} />
      </Route>

      <Route element={<ProtectedRoute allowedRole="doctor" />}>
        <Route path="/doctor/dashboard" element={<DoctorQueue />} />
        <Route path="/doctor/case/:caseId" element={<CaseReview />} />
        <Route path="/doctor/finalize/:caseId" element={<FinalDiagnosis />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
