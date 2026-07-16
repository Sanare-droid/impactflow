import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getDb } from "@/lib/db";
import { clearSession, hydrateSession, persistSession } from "@/lib/session";
import { api } from "@/lib/api";

type AuthContextValue = {
  authed: boolean;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        await getDb();
      } catch {
        /* web / unsupported */
      }
      const ok = await hydrateSession();
      setAuthed(ok);
      setReady(true);
    })();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const tokens = await api.login(email.trim(), password);
    if (tokens.mfa_required) {
      throw new Error("MFA required — complete setup on web first");
    }
    const orgId = tokens.user?.primary_organization_id ?? null;
    await persistSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      organization_id: orgId,
    });
    if (tokens.user?.first_name) {
      const { setProfileField } = await import("@/lib/db/repo");
      await setProfileField("first_name", tokens.user.first_name);
    }
    setAuthed(true);
  }, []);

  const signOut = useCallback(async () => {
    await clearSession();
    setAuthed(false);
  }, []);

  const value = useMemo(
    () => ({ authed, ready, signIn, signOut }),
    [authed, ready, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
