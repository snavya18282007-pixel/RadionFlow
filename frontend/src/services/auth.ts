import type { UserRole } from "../types";

export type LoginRoleOption = UserRole | "admin";

export const loginRoleOptions: Array<{ label: string; value: LoginRoleOption }> = [
  { label: "Lab Technician", value: "lab_technician" },
  { label: "Doctor", value: "doctor" },
  { label: "Admin", value: "admin" },
];

export function getDashboardPath(role: UserRole) {
  return role === "doctor" ? "/doctor/dashboard" : "/lab/dashboard";
}
