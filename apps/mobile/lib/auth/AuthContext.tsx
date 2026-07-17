import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { getDb, wipeLocalData } from "@/lib/db";
import { clearSession, hydrateSession, persistSession } from "@/lib/session";
import { api, type MyOrganization } from "@/lib/api";

type PendingLogin = {
  access_token: string;
  refresh_token: string;
  user_id: string;
  first_name?: string;
};

type AuthContextValue = {
  authed: boolean;
  ready: boolean;
  /** Non-null while the signed-in user belongs to >1 organization and must pick one. */
  orgChoices: MyOrganization[] | null;
  signIn: (email: string, password: string) => Promise<void>;
  pickOrganization: (organizationId: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(false);
  const [ready, setReady] = useState(false);
  const [orgChoices, setOrgChoices] = useState<MyOrganization[] | null>(null);
  const pendingLogin = useRef<PendingLogin | null>(null);

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

  const finalizeLogin = useCallback(
    async (login: PendingLogin, organizationId: string) => {
      await wipeLocalData();
      await persistSession({
        access_token: login.access_token,
        refresh_token: login.refresh_token,
        organization_id: organizationId,
        user_id: login.user_id,
      });
      const { setProfileField } = await import("@/lib/db/repo");
      await setProfileField("user_id", login.user_id);
      await setProfileField("organization_id", organizationId);
      if (login.first_name) {
        await setProfileField("first_name", login.first_name);
      }
      pendingLogin.current = null;
      setOrgChoices(null);
      setAuthed(true);
    },
    [],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const tokens = await api.login(email.trim(), password);
      if (tokens.mfa_required) {
        throw new Error(
          "Complete MFA on the web app first. Mobile MFA is not available yet — sign in at impactflowai.netlify.app to finish verification, then return here.",
        );
      }
      const userId = tokens.user?.id ?? null;
      if (!userId) {
        throw new Error(
          "Unable to resolve your user id from login. Please try again or contact support.",
        );
      }
      // Set the token on the client (without an org yet) so we can query which
      // organizations this user belongs to — permissions are re-derived per
      // request from X-Organization-Id, so no org needs to be chosen yet.
      api.setSession({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        user_id: userId,
      });
      const login: PendingLogin = {
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        user_id: userId,
        first_name: tokens.user?.first_name,
      };

      let organizations: MyOrganization[] = [];
      try {
        organizations = await api.myOrganizations();
      } catch {
        organizations = [];
      }

      if (organizations.length > 1) {
        pendingLogin.current = login;
        setOrgChoices(organizations);
        return;
      }

      const orgId =
        organizations[0]?.id ??
        tokens.organization_id ??
        tokens.user?.primary_organization_id ??
        null;
      if (!orgId) {
        throw new Error(
          "Your account has no organization. Contact your admin to be invited to a workspace before using the field app.",
        );
      }
      await finalizeLogin(login, orgId);
    },
    [finalizeLogin],
  );

  const pickOrganization = useCallback(
    async (organizationId: string) => {
      if (!pendingLogin.current) {
        throw new Error("No pending login — please sign in again.");
      }
      await finalizeLogin(pendingLogin.current, organizationId);
    },
    [finalizeLogin],
  );

  const signOut = useCallback(async () => {
    pendingLogin.current = null;
    setOrgChoices(null);
    await clearSession();
    await wipeLocalData();
    setAuthed(false);
  }, []);

  const value = useMemo(
    () => ({ authed, ready, orgChoices, signIn, pickOrganization, signOut }),
    [authed, ready, orgChoices, signIn, pickOrganization, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
