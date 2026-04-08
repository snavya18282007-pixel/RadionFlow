import type { ReactNode } from "react";

interface InputProps {
  label: string;
  children: ReactNode;
}

export function Input({ label, children }: InputProps) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
