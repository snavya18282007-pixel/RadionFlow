import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  block?: boolean;
}

export function Button({ variant = "primary", block = false, className = "", ...props }: ButtonProps) {
  const variantClass =
    variant === "secondary" ? "button button-secondary" : variant === "ghost" ? "button button-ghost" : "button";

  return <button className={`${variantClass}${block ? " button-block" : ""} ${className}`.trim()} {...props} />;
}
