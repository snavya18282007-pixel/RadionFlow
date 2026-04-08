import type { ReactNode } from "react";

import { PageLayout } from "./PageLayout";
import { useAuth } from "../context/AuthContext";
import type { NavigationItem } from "./Sidebar";

interface AppShellProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const { auth, signOut } = useAuth();

  const navItems: NavigationItem[] =
    auth?.role === "doctor"
      ? [
          {
            to: "/doctor/dashboard",
            label: "Doctor Queue",
            matchPrefixes: ["/doctor/dashboard", "/doctor/case", "/doctor/finalize"],
          },
        ]
      : [
          { to: "/lab/dashboard", label: "Dashboard", matchPrefixes: ["/lab/dashboard"] },
          { to: "/lab/register", label: "Register Patient", matchPrefixes: ["/lab/register"] },
          {
            to: "/lab/upload",
            label: "Upload Report",
            matchPrefixes: ["/lab/upload", "/lab/processing", "/lab/result"],
          },
        ];

  return (
    <PageLayout
      workspaceLabel={auth?.role === "doctor" ? "Doctor Workspace" : "Lab Technician Workspace"}
      roleLabel={auth?.role === "doctor" ? "Doctor" : "Lab Technician"}
      userDisplayName={auth?.displayName}
      onSignOut={signOut}
      navItems={navItems}
    >
      <div className="app-shell">
        <section className="page-heading">
          <p className="eyebrow">{auth?.role === "doctor" ? "Doctor Console" : "Lab Intake Console"}</p>
          <h1>{title}</h1>
          <p className="shell-subtitle">{subtitle}</p>
        </section>
        <div className="shell-content">{children}</div>
      </div>
    </PageLayout>
  );
}
