import { useCallback, useState } from "react";

/** Tracks busy/error state for a sequence of async API calls. */
export function useRunner() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(fn: () => Promise<T>, then: (value: T) => void) => {
    setBusy(true);
    setError(null);
    try {
      then(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, run };
}
