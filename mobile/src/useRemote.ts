import { useCallback, useEffect, useState } from "react";

import { friendlyError } from "./components/ui";

export interface Remote<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/** Loads once on mount and again on `reload`. `load` must be stable, so wrap it in useCallback. */
export function useRemote<T>(load: () => Promise<T>): Remote<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setLoading(true);
    load()
      .then((value) => live && (setData(value), setError(null)))
      .catch((cause: unknown) => live && setError(friendlyError(cause)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [load, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  return { data, error, loading, reload };
}
