// Port of the design's renderVals(): derives every bound view-model field from
// the real cryobrain.json. Formulas are kept identical to CryoBrains.dc.html so
// the React charts are pixel-faithful to the original design.
import type { CryoData, ParetoPoint, ReplayEvent } from "./types";
import { C } from "../theme";

export interface NpuItem { year: string; name: string; note: string; dot: string }
export interface AgentItem { idx: string; name: string; role: string; color: string }
export interface ParetoDot {
  cx: number; cy: number; ler: number; area: number; latency: number; hash: string; frontier: boolean;
}
export interface BenchRow { id: string; ler: number; area: number; latency: number; status: string }
export interface LayerBadge { k: string; passed: boolean; skipped: boolean }
export interface ExaLink { title: string; url: string }
export interface FifoDot { x: number; y: number; tp: number }
export interface AdoptionStep { step: string; label: string; bg: string; fg: string; arrow: boolean }
export interface WedgeItem { num: string; title: string; note: string; bg: string; fg: string }
export interface SpecRow { k: string; v: string }

export interface SwarmHud {
  idle: boolean;
  design: string;
  agent: string;
  action: string;
  detail: string;
  statusLabel: string;
  accent: string;
  measured: boolean;
}

export interface Charts {
  rtlLines: string[];
  layers: LayerBadge[];
  paretoDec: ParetoDot[];
  paretoFifo: ParetoDot[];
  bench: BenchRow[];
  exa: ExaLink[];
  cycles: { cycle: number }[];
  synLine: string;
  corrLine: string;
  svLine: string;
  cvLine: string;
  fifoPath: string;
  fifoDots: FifoDot[];
  marathonCompleted: number;
  researchQuery: string;
}

// ---- static view-model (matches renderVals) ----
export const NPU: NpuItem[] = [
  { year: "2017", name: "Apple A11", note: "First Neural Engine — Face ID, on-device ML.", dot: "#8a8a93" },
  { year: "2024", name: "Apple M4", note: "38 TOPS — the NPU is now a central chip block.", dot: "#8a8a93" },
  { year: "2024", name: "Intel Core Ultra", note: "CPU + GPU + NPU fused for AI PCs.", dot: "#8a8a93" },
  { year: "2024", name: "AMD XDNA", note: "Dedicated AI engine for efficient inference.", dot: "#8a8a93" },
  { year: "2040", name: "CryoBrain QC-NPU", note: "The neural engine for quantum control.", dot: "#64d2ff" },
];

export const AGENTS: AgentItem[] = [
  { idx: "01", name: "Research", role: "Pulls decoder & chip-design literature via Exa.", color: "#64d2ff" },
  { idx: "02", name: "Planner", role: "Chooses the next experiment to run.", color: "#64d2ff" },
  { idx: "03", name: "Architect", role: "Proposes a decoder / NPU design.", color: "#64d2ff" },
  { idx: "04", name: "RTL", role: "Generates synthesizable Verilog.", color: "#0a84ff" },
  { idx: "05", name: "Measurement", role: "Runs Stim + Verilator + Yosys.", color: "#0a84ff" },
  { idx: "06", name: "Verifier", role: "Gates the design across 5 layers.", color: "#ffd60a" },
  { idx: "07", name: "Scorer", role: "Computes the measured reward.", color: "#30d158" },
  { idx: "08", name: "Memory", role: "Stores verified winners and failures.", color: "#30d158" },
];

export const PROOF_FILES: string[] = [
  "measured_climb.json",
  "measured_pareto.json",
  "event_log.jsonl",
  "generated_decoder.sv",
  "verification_report.json",
];

export const ADOPTION: AdoptionStep[] = [
  { step: "Source", label: "Exa ContextPack", bg: "#0a0c10", fg: "#f5f5f7", arrow: true },
  { step: "Plan", label: "Planner decision", bg: "#fff", fg: "#0a0a0c", arrow: true },
  { step: "Propose", label: "Architect proposal", bg: "#fff", fg: "#0a0a0c", arrow: true },
  { step: "Measure", label: "Verified result", bg: "rgba(48,209,88,.12)", fg: "#1d8c3e", arrow: true },
  { step: "Remember", label: "Memory tag", bg: "rgba(10,132,255,.1)", fg: "#0a4da8", arrow: false },
];

export const WEDGE: WedgeItem[] = [
  { num: "01", title: "Verifiable hardware-design environments", note: "The measured loop, sold to AI labs and EDA teams building hardware agents.", bg: "#fff", fg: "#0a0a0c" },
  { num: "02", title: "Verified decoder / control-brain blocks", note: "Drop-in, measured, signed-off IP for quantum control.", bg: "#0a0c10", fg: "#f5f5f7" },
  { num: "03", title: "Full quantum control NPU platform", note: "The co-located AI brain for the 2040 quantum stack.", bg: "linear-gradient(160deg,#0a84ff,#0a4da8)", fg: "#fff" },
];

export const CHIP_SPEC: SpecRow[] = [
  { k: "Input", v: "syndrome streams" },
  { k: "Output", v: "corrections + confidence" },
  { k: "Constraints", v: "low latency · low power · cryo" },
  { k: "Built today", v: "decoder RTL + measured env" },
  { k: "Future chip", v: "adaptive control NPU @ QPU" },
];

// ---- swarm HUD builder (per-agent strings, identical to design) ----
export function buildSwarmHud(ev: ReplayEvent | null): SwarmHud {
  if (!ev) {
    return {
      idle: true,
      design: "—",
      agent: "awaiting replay",
      action: "",
      detail: "Replaying measured events from event_log.jsonl",
      statusLabel: "idle",
      accent: C.muted3,
      measured: false,
    };
  }
  const p = ev.params || ({} as NonNullable<ReplayEvent["params"]>);
  let detail = "";
  let statusLabel = "flow";
  let accent: string = C.cyan;
  if (ev.agent === "Research") detail = `${ev.urls ?? 5} sources retrieved · Exa`;
  else if (ev.agent === "Architect")
    detail = `bw ${p.bitwidth} · ${p.num_layers} layers · pipe ${p.pipeline_depth} · win ${p.window_length}`;
  else if (ev.agent === "RTL") detail = `synthesizable Verilog · ${ev.rtl_hash || ""}`;
  else if (ev.agent === "Measurement") {
    detail = `LER ${ev.ler} · suppression ${ev.suppression}`;
    accent = C.blue;
  } else if (ev.agent === "Verifier") {
    const ok = ev.gates !== false;
    detail = ok
      ? `all gates passed · ${(ev.layers || []).join(" ")}`
      : `gate failed · ${(ev.layers || []).join(" ")}`;
    statusLabel = ok ? "verified" : "rejected";
    accent = ok ? C.green : C.red;
  } else if (ev.agent === "Scorer") {
    const ok = ev.valid !== false;
    detail = `reward ${ev.reward} · ${ok ? "valid" : "invalid"}`;
    statusLabel = ok ? "scored" : "rejected";
    accent = ok ? C.green : C.red;
  } else if (ev.agent === "Memory") {
    detail = `stored variant · ${ev.rtl_hash || ""}`;
    statusLabel = "remembered";
    accent = C.green;
  }
  return {
    idle: false,
    design: ev.design,
    agent: ev.agent,
    action: ev.action,
    detail,
    statusLabel,
    accent,
    measured: !!ev.measured,
  };
}

const EMPTY_CHARTS: Charts = {
  rtlLines: [], layers: [], paretoDec: [], paretoFifo: [], bench: [], exa: [],
  cycles: [], synLine: "", corrLine: "", svLine: "", cvLine: "", fifoPath: "",
  fifoDots: [], marathonCompleted: 0, researchQuery: "",
};

// ---- chart geometry (real data) ----
export function buildCharts(D: CryoData): Charts {
  const sm = D.waveform.samples;
  if (sm.length === 0) return EMPTY_CHARTS;
  const t0 = sm[0].t;
  const t1 = sm[sm.length - 1].t;
  const span = t1 - t0 || 1;
  const wx = (t: number) => ((t - t0) / span) * 960;

  const synLine = sm.map((s) => `${wx(s.t).toFixed(1)},${(38 - (s.syn / 255) * 32).toFixed(1)}`).join(" ");
  const corrLine = sm.map((s) => `${wx(s.t).toFixed(1)},${(38 - (s.corr / 15) * 32).toFixed(1)}`).join(" ");
  const svLine = sm.map((s) => `${wx(s.t).toFixed(1)},${(18 - s.sv * 15).toFixed(1)}`).join(" ");
  const cvLine = sm.map((s) => `${wx(s.t).toFixed(1)},${(18 - s.cv * 15).toFixed(1)}`).join(" ");

  // deterministic sin-hash jitter — same constants as the design, so the
  // scatter renders identically every load (not Math.random()).
  const pmap = (pts: ParetoPoint[], jit: boolean): ParetoDot[] =>
    pts.map((p, i) => {
      const j = jit ? (Math.sin(i * 12.9898) * 43758.5453) % 1 : 0;
      const j2 = jit ? (Math.sin(i * 78.233) * 12543.123) % 1 : 0;
      return {
        cx: (Math.log2(Math.max(p.area, 1)) / Math.log2(512)) * 92 + 4 + j * 5,
        cy: 92 - (1 - p.ler) * 84 + j2 * 5,
        ler: p.ler,
        area: p.area,
        latency: p.latency,
        hash: p.hash,
        frontier: p.frontier,
      };
    });

  const paretoDec = pmap(D.pareto.decoder, true);
  const paretoFifo = pmap(D.pareto.fifo, false);

  const fpad = 24;
  const fifo = D.climb.fifo;
  const fifoPath = fifo
    .map((h, i, a) => {
      const x = fpad + (a.length > 1 ? i / (a.length - 1) : 0.5) * (300 - 2 * fpad);
      const y = 120 - h.throughput * 96;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const fifoDots: FifoDot[] = fifo.map((h, i, a) => ({
    x: fpad + (a.length > 1 ? i / (a.length - 1) : 0.5) * (300 - 2 * fpad),
    y: 120 - h.throughput * 96,
    tp: h.throughput,
  }));

  const bench: BenchRow[] = D.pareto.decoder.slice(0, 6).map((p) => ({
    id: `cryo@${p.hash}`,
    ler: p.ler,
    area: p.area,
    latency: p.latency,
    status: "verified",
  }));

  const layers: LayerBadge[] = Object.keys(D.verify.layers).map((k) => ({
    k,
    passed: D.verify.layers[k].passed,
    skipped: D.verify.layers[k].skipped,
  }));

  const exa: ExaLink[] = (D.marathon.exa_titles || []).map((t, i) => ({
    title: t,
    url: (D.marathon.exa_urls || [])[i],
  }));

  return {
    rtlLines: D.rtl.split("\n"),
    layers,
    paretoDec,
    paretoFifo,
    bench,
    exa,
    cycles: (D.marathon.cycles || []).map((c) => ({ cycle: c.cycle })),
    synLine,
    corrLine,
    svLine,
    cvLine,
    fifoPath,
    fifoDots,
    marathonCompleted: D.marathon.completed,
    researchQuery: D.research.query,
  };
}
