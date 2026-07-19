"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  fetchMe,
  getStoredIdToken,
  setStoredIdToken,
} from "@/lib/api";
import type { MeResponse } from "@/lib/types";

interface AuthState {
  user: MeResponse | null;
  idToken: string | null;
  loading: boolean;
  error: string | null;
  loginWithIdToken: (token: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    setStoredIdToken(null);
    setIdToken(null);
    setUser(null);
    setError(null);
  }, []);

  const loginWithIdToken = useCallback(async (token: string) => {
    setLoading(true);
    setError(null);
    try {
      const me = await fetchMe(token);
      setStoredIdToken(token);
      setIdToken(token);
      setUser(me);
    } catch (err) {
      setStoredIdToken(null);
      setIdToken(null);
      setUser(null);
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshMe = useCallback(async () => {
    const token = getStoredIdToken();
    if (!token) {
      setUser(null);
      setIdToken(null);
      return;
    }
    const me = await fetchMe(token);
    setUser(me);
    setIdToken(token);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = getStoredIdToken();
      if (!token) {
        if (!cancelled) setLoading(false);
        return;
      }
      try {
        const me = await fetchMe(token);
        if (!cancelled) {
          setIdToken(token);
          setUser(me);
        }
      } catch {
        if (!cancelled) {
          setStoredIdToken(null);
          setIdToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      idToken,
      loading,
      error,
      loginWithIdToken,
      logout,
      refreshMe,
    }),
    [user, idToken, loading, error, loginWithIdToken, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
