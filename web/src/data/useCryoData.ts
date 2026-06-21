import { useEffect, useState } from "react";
import type { CryoData } from "./types";

interface State {
  data: CryoData | null;
  error: string | null;
}

// Loads the real measured bundle from public/data/cryobrain.json.
// No fallback / mock data: if the fetch fails we surface the error and the
// UI renders its honest "awaiting data" placeholders.
export function useCryoData(): State {
  const [state, setState] = useState<State>({ data: null, error: null });

  useEffect(() => {
    let alive = true;
    fetch(`${import.meta.env.BASE_URL}data/cryobrain.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: CryoData) => {
        if (alive) setState({ data: d, error: null });
      })
      .catch((e: unknown) => {
        if (alive) setState({ data: null, error: String(e) });
      });
    return () => {
      alive = false;
    };
  }, []);

  return state;
}
