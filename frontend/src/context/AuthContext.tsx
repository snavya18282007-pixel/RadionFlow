import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

import { loginUser } from "../lib/api";
import { clearAuth, loadAuth, saveAuth } from "../lib/storage";
import type { AuthLoginPayload, AuthState } from "../types";

interface AuthContextValue {
  auth: AuthState | null;
  signIn: (payload: AuthLoginPayload) => Promise<AuthState>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(() => loadAuth());

  async function signIn(payload: AuthLoginPayload) {
    const response = await loginUser(payload);
    const nextAuth = {
      token: response.token,
      role: response.role,
      displayName: response.display_name,
      email: response.email,
    } satisfies AuthState;
    setAuth(nextAuth);
    saveAuth(nextAuth);
    return nextAuth;
  }

  function signOut() {
    setAuth(null);
    clearAuth();
  }

  return <AuthContext.Provider value={{ auth, signIn, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
