import { useCallback, useEffect, useRef, useState } from "react";
import { C } from "./theme";
import { useCryoData } from "./data/useCryoData";
import {
  AGENTS,
  ADOPTION,
  CHIP_SPEC,
  NPU,
  PROOF_FILES,
  WEDGE,
  buildCharts,
  buildSwarmHud,
  type Charts,
} from "./data/derive";
import type { ReplayEvent } from "./data/types";

import { TopNav, DotNav } from "./sections/Nav";
import { GlobalKeyframes } from "./sections/common";
import { S01Hero } from "./sections/S01Hero";
import { S02Problem } from "./sections/S02Problem";
import { S03Npu } from "./sections/S03Npu";
import { S04TwoLoops } from "./sections/S04TwoLoops";
import { S05Built } from "./sections/S05Built";
import { S06Swarm } from "./sections/S06Swarm";
import { S07Evidence } from "./sections/S07Evidence";
import { S08Benchmark } from "./sections/S08Benchmark";
import { S09Pareto } from "./sections/S09Pareto";
import { S10Research } from "./sections/S10Research";
import { S11Memory } from "./sections/S11Memory";
import { S12Chip } from "./sections/S12Chip";
import { S13Business } from "./sections/S13Business";
import { S14Close } from "./sections/S14Close";

const SECTION_COUNT = 14;

export default function App() {
  const { data, error } = useCryoData();
  const rootRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  const [swarmEvent, setSwarmEvent] = useState<ReplayEvent | null>(null);

  const goTo = useCallback((i: number) => {
    const root = rootRef.current;
    if (!root) return;
    const secs = Array.from(root.querySelectorAll<HTMLElement>("[data-section]"));
    const target = secs[i];
    if (target) root.scrollTo({ top: target.offsetTop, behavior: "smooth" });
  }, []);
  const next = useCallback(() => goTo(Math.min(active + 1, SECTION_COUNT - 1)), [active, goTo]);
  const prev = useCallback(() => goTo(Math.max(active - 1, 0)), [active, goTo]);

  // active-section observer
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const secs = Array.from(root.querySelectorAll<HTMLElement>("[data-section]"));
    if (!secs.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting && en.intersectionRatio > 0.5) {
            const i = secs.indexOf(en.target as HTMLElement);
            if (i >= 0) setActive(i);
          }
        });
      },
      { root, threshold: [0.5] },
    );
    secs.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, [data]);

  // keyboard nav
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown" || e.key === "PageDown") {
        e.preventDefault();
        next();
      } else if (e.key === "ArrowUp" || e.key === "PageUp") {
        e.preventDefault();
        prev();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev]);

  const charts: Charts | null = data ? buildCharts(data) : null;
  const hud = buildSwarmHud(swarmEvent);

  return (
    <div
      id="cb-root"
      ref={rootRef}
      style={{
        position: "fixed",
        inset: 0,
        overflowY: "scroll",
        scrollSnapType: "y mandatory",
        background: C.bg,
        color: C.ink,
        fontFamily:
          "-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','Helvetica Neue',Helvetica,Arial,sans-serif",
        WebkitFontSmoothing: "antialiased",
        lineHeight: 1.5,
        scrollbarWidth: "none",
      }}
    >
      <GlobalKeyframes />
      <TopNav era={data?.meta.data_era ?? "measured"} marathon={data?.marathon} />
      <DotNav active={active} goTo={goTo} count={SECTION_COUNT} />

      <S01Hero next={next} decoder={data?.decoder} />
      <S02Problem />
      <S03Npu npu={NPU} />
      <S04TwoLoops />
      <S05Built agents={AGENTS} proofFiles={PROOF_FILES} />
      <S06Swarm data={data} hud={hud} onEvent={setSwarmEvent} active={active === 5} />
      <S07Evidence charts={charts} decoder={data?.decoder} />
      <S08Benchmark charts={charts} climbFifo={data?.climb.fifo} />
      <S09Pareto charts={charts} pareto={data?.pareto} />
      <S10Research charts={charts} adoption={ADOPTION} />
      <S11Memory charts={charts} marathon={data?.marathon} />
      <S12Chip chipSpec={CHIP_SPEC} />
      <S13Business wedge={WEDGE} />
      <S14Close />

      {error && (
        <div
          style={{
            position: "fixed",
            bottom: 16,
            left: 16,
            zIndex: 99,
            padding: "10px 14px",
            borderRadius: 10,
            background: "rgba(255,69,58,.15)",
            border: "1px solid rgba(255,69,58,.4)",
            color: C.red,
            fontSize: 12,
            fontFamily: "ui-monospace,'SF Mono',Menlo,monospace",
          }}
        >
          data load failed: {error} — expected public/data/cryobrain.json
        </div>
      )}
    </div>
  );
}
