import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import NetInfo from "@react-native-community/netinfo";
import { queueCounts } from "@/lib/db/repo";
import { getLastSyncAt, runSync, type SyncResult } from "@/lib/sync/engine";

type SyncContextValue = {
  online: boolean;
  syncing: boolean;
  pending: number;
  failed: number;
  lastSyncAt: string | null;
  lastResult: SyncResult | null;
  error: string | null;
  refreshStatus: () => Promise<void>;
  syncNow: () => Promise<void>;
  retryFailed: () => Promise<void>;
};

const SyncContext = createContext<SyncContextValue | null>(null);

export function SyncProvider({ children }: { children: ReactNode }) {
  const [online, setOnline] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [pending, setPending] = useState(0);
  const [failed, setFailed] = useState(0);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const counts = await queueCounts();
      setPending(counts.pending);
      setFailed(counts.failed);
      setLastSyncAt(await getLastSyncAt());
    } catch {
      /* db may not be ready on web */
    }
  }, []);

  const syncNow = useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await runSync();
      setLastResult(result);
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }, [refreshStatus]);

  const retryFailed = useCallback(async () => {
    const { retryFailedMutations } = await import("@/lib/db/repo");
    await retryFailedMutations();
    await refreshStatus();
    if (online) await syncNow();
  }, [online, refreshStatus, syncNow]);

  useEffect(() => {
    void refreshStatus();
    const unsub = NetInfo.addEventListener((state) => {
      const isOnline = Boolean(state.isConnected && state.isInternetReachable !== false);
      setOnline(isOnline);
    });
    return () => unsub();
  }, [refreshStatus]);

  useEffect(() => {
    if (online && pending > 0 && !syncing) {
      void syncNow();
    }
  }, [online]); // eslint-disable-line react-hooks/exhaustive-deps

  const value = useMemo(
    () => ({
      online,
      syncing,
      pending,
      failed,
      lastSyncAt,
      lastResult,
      error,
      refreshStatus,
      syncNow,
      retryFailed,
    }),
    [
      online,
      syncing,
      pending,
      failed,
      lastSyncAt,
      lastResult,
      error,
      refreshStatus,
      syncNow,
      retryFailed,
    ],
  );

  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>;
}

export function useSync() {
  const ctx = useContext(SyncContext);
  if (!ctx) throw new Error("useSync must be used within SyncProvider");
  return ctx;
}
