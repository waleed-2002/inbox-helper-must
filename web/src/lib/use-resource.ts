"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Snapshot<K, T> = { key: K; request: number; value?: T; error?: unknown };

export function useResource<K, T>(key: K | null, load: (key: K, signal: AbortSignal) => Promise<T>) {
  const [snapshot, setSnapshot] = useState<Snapshot<K, T>>();
  const [request, setRequest] = useState(0);
  const active = useRef<{ key: K; request: number; controller: AbortController }>(null);

  useEffect(() => {
    if (key === null) return;
    const controller = new AbortController();
    active.current = { key, request, controller };
    load(key, controller.signal).then(
      (value) => {
        if (!controller.signal.aborted) setSnapshot({ key, request, value });
      },
      (error: unknown) => {
        if (!controller.signal.aborted) setSnapshot((prev) =>
          ({ key, request, value: prev?.key === key ? prev.value : undefined, error }));
      },
    );
    return () => {
      controller.abort();
      if (active.current?.controller === controller) active.current = null;
    };
  }, [key, load, request]);

  const refresh = useCallback(() => setRequest((value) => value + 1), []);
  const replace = useCallback((resultKey: K, value: T) => {
    if (active.current?.key !== resultKey) return;
    active.current.controller.abort();
    setSnapshot({ key: resultKey, request: active.current.request, value });
  }, []);
  const current = snapshot?.key === key ? snapshot : undefined;
  return {
    value: current?.value, error: current?.error, loading: key !== null && !current,
    refreshing: key !== null && current?.request !== request, refresh, replace,
  };
}
