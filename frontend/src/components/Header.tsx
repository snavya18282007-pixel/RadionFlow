interface HeaderProps {
  workspaceLabel: string;
  roleLabel: string;
  userDisplayName?: string;
  onSignOut: () => void;
}

export function Header({ workspaceLabel, roleLabel, userDisplayName, onSignOut }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__name">RADION AI</span>
        <span className="app-header__workspace">{workspaceLabel}</span>
      </div>

      <div className="app-header__meta">
        <div className="user-chip user-chip--header">
          <span className="user-chip__role">{roleLabel}</span>
          <strong>{userDisplayName ?? "Clinical User"}</strong>
        </div>
        <button className="button button-ghost" type="button" onClick={onSignOut}>
          Sign Out
        </button>
      </div>
    </header>
  );
}
