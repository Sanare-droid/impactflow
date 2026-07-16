"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, type UserBrief } from "@/lib/api";

type AuthState = {
  user: UserBrief | null;
  loading: boolean;
  setUser: (user: UserBrief | null) => void;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserBrief | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = async () => {
    api.hydrateFromStorage();
    if (!api.hasSession) {
      setUser(null);
      return;
    }
    const me = await api.me();
    setUser(me);
    localStorage.setItem("if_user", JSON.stringify(me));
  };

  useEffect(() => {
    (async () => {
      try {
        api.hydrateFromStorage();
        if (api.hasSession) {
          await refreshMe();
        }
      } catch {
        api.clearSession();
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      setUser,
      refreshMe,
      logout: async () => {
        await api.logout();
        setUser(null);
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
