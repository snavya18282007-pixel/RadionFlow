import { NavLink, useLocation } from "react-router-dom";

export interface NavigationItem {
  to: string;
  label: string;
  matchPrefixes?: string[];
}

interface SidebarProps {
  workspaceLabel: string;
  navItems: NavigationItem[];
}

export function Sidebar({ workspaceLabel, navItems }: SidebarProps) {
  const location = useLocation();

  return (
    <aside className="app-sidebar">
      <div className="app-sidebar__intro">
        <h2>Workflow</h2>
        <p>{workspaceLabel}</p>
      </div>

      <nav className="sidebar-nav" aria-label={`${workspaceLabel} navigation`}>
        {navItems.map((item) => {
          const isActive = (item.matchPrefixes ?? [item.to]).some((prefix) => location.pathname.startsWith(prefix));
          return (
            <NavLink
              key={`${item.to}-${item.label}`}
              to={item.to}
              className={isActive ? "sidebar-link sidebar-link--active" : "sidebar-link"}
            >
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
