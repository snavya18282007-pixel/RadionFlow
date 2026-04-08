import type { ReactNode } from "react";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import type { NavigationItem } from "./Sidebar";

interface PageLayoutProps {
  workspaceLabel: string;
  roleLabel: string;
  userDisplayName?: string;
  onSignOut: () => void;
  navItems: NavigationItem[];
  children: ReactNode;
}

export function PageLayout({
  workspaceLabel,
  roleLabel,
  userDisplayName,
  onSignOut,
  navItems,
  children,
}: PageLayoutProps) {
  return (
    <div className="page-layout">
      <Header
        workspaceLabel={workspaceLabel}
        roleLabel={roleLabel}
        userDisplayName={userDisplayName}
        onSignOut={onSignOut}
      />
      <div className="page-layout__body">
        <Sidebar workspaceLabel={workspaceLabel} navItems={navItems} />
        <main className="page-layout__main">{children}</main>
      </div>
    </div>
  );
}
