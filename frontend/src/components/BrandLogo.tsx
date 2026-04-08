import type { HTMLAttributes } from "react";

interface BrandLogoProps extends HTMLAttributes<HTMLDivElement> {
  showWordmark?: boolean;
  subtitle?: string;
}

function LogoMark() {
  return (
    <svg aria-hidden="true" className="h-14 w-14 text-[var(--primary)]" viewBox="0 0 64 64" fill="none">
      <path
        d="M27 6h10v9h9v9h12v16H46v9h-9v9H27v-9h-9v-9H6V24h12v-9h9V6Z"
        fill="rgba(31,58,95,0.05)"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinejoin="round"
      />
      <circle cx="32" cy="32" r="10.5" stroke="var(--accent)" strokeWidth="2.6" />
      <path d="M32 22v20M22 32h20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" opacity="0.48" />
      <path d="M39 20.5a13 13 0 0 1 0 23" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M42.5 25h5.5M42.5 39h5.5" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="32" cy="32" r="3.2" fill="white" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export function BrandLogo({ showWordmark = true, subtitle, className = "", ...rest }: BrandLogoProps) {
  return (
    <div className={`flex items-start gap-4 ${className}`.trim()} {...rest}>
      <div className="flex h-16 w-16 items-center justify-center rounded-[12px] border border-[var(--border)] bg-[var(--surface)]">
        <LogoMark />
      </div>
      {showWordmark ? (
        <div className="grid gap-1">
          <span className="text-[32px] font-semibold leading-none tracking-[-0.03em] text-[var(--ink)]">Radion AI</span>
          <span className="text-sm font-medium text-[var(--ink-soft)]">
            {subtitle ?? "Clinical Radiology Intelligence Platform"}
          </span>
        </div>
      ) : null}
    </div>
  );
}
