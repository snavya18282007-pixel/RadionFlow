interface StatusPillProps {
  value: string;
  kind?: "triage" | "status";
}

function normalizeValue(value: string) {
  return value.toLowerCase().replace(/\s+/g, "-").replace(/_/g, "-");
}

export function StatusPill({ value, kind = "status" }: StatusPillProps) {
  return <span className={`pill pill--${kind} pill--${normalizeValue(value)}`}>{value}</span>;
}
