import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getDb, wipeLocalData } from "@/lib/db";
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
    api.setOnSessionExpired(() => {
      setAuthed(false);
    });
    return () => api.setOnSessionExpired(null);
  }, []);

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
      throw new Error(
        "Complete MFA on the web app first. Mobile MFA is not available yet — sign in at impactflowai.netlify.app to finish verification, then return here.",
      );
    }
    const orgId =
      tokens.organization_id ?? tokens.user?.primary_organization_id ?? null;
    const userId = tokens.user?.id ?? null;
    if (!orgId) {
      throw new Error(
        "Your account has no organization. Contact your admin to be invited to a workspace before using the field app.",
      );
    }
    if (!userId) {
      throw new Error(
        "Unable to resolve your user id from login. Please try again or contact support.",
      );
    }
    await wipeLocalData();
    await persistSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      organization_id: orgId,
      user_id: userId,
    });
    const { setProfileField } = await import("@/lib/db/repo");
    await setProfileField("user_id", userId);
    await setProfileField("organization_id", orgId);
    if (tokens.user?.first_name) {
      await setProfileField("first_name", tokens.user.first_name);
    }
    setAuthed(true);
  }, []);

  const signOut = useCallback(async () => {
    await clearSession();
    await wipeLocalData();
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
