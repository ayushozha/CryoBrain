// Types for public/data/cryobrain.json — the real measured CryoBrain artifact bundle.
// Mirrors the structure produced by the swarm run on 2026-06-21.

export interface CryoMeta {
  name: string;
  tagline: string;
  data_era: string;
  generated_at: string;
}

export interface DecoderDesign {
  bitwidth: number;
  num_layers: number;
  parallelism: number;
  pipeline_depth: number;
  window_length: number;
}

export interface Decoder {
  ler: number;
  mwpm_ler: number;
  suppression: number;
  area_um2: number;
  latency_cycles: number;
  power_mw: number;
  cell_count: number;
  reward: number;
  valid: boolean;
  shots: number;
  vector_source: string;
  benchmark_vectors: number;
  benchmark_failures: number;
  design: DecoderDesign;
}

export interface VerifyLayer {
  log_path: string;
  passed: boolean;
  skipped: boolean;
  benchmark_failures?: number;
  benchmark_vectors?: number;
}

export interface Verify {
  all_passed: boolean;
  layers: Record<string, VerifyLayer>;
  layers_passed: string[];
}

export interface WaveformSample {
  t: number;
  clk: number;
  sv: number;
  syn: number;
  cv: number;
  corr: number;
}

export interface Waveform {
  signals: string[];
  latency_cycles: number;
  samples: WaveformSample[];
}

export interface ParetoPoint {
  ler: number;
  area: number;
  latency: number;
  hash: string;
  frontier: boolean;
}

export interface Pareto {
  count: number;
  frontier_count: number;
  accuracy_axis: string;
  hardware_axis: string;
  decoder: ParetoPoint[];
  fifo: ParetoPoint[];
}

export interface FifoClimbStep {
  step: number;
  throughput: number;
  suppression: number;
  rtl_hash: string;
}

export interface Climb {
  decoder: Array<Record<string, unknown>>;
  fifo: FifoClimbStep[];
  memory_ab: Record<string, unknown>;
}

export interface MarathonCycle {
  cycle: number;
  fifo_start: number;
  fifo_end: number;
  fifo_delta: number;
  decoder_accepted: number;
  fifo_accepted: number;
  planner_accepted: number;
}

export interface Marathon {
  requested: number;
  completed: number;
  status: string;
  steps_per_agent: number;
  sponsors: Record<string, unknown>;
  cycles: MarathonCycle[];
  exa_urls: string[];
  exa_titles: string[];
}

export interface Research {
  query: string;
  hit_count: number;
  urls: string[];
}

export type AgentName =
  | "Research"
  | "Planner"
  | "Architect"
  | "RTL"
  | "Measurement"
  | "Verifier"
  | "Scorer"
  | "Memory";

export interface ReplayEvent {
  seq: number;
  design: string;
  agent: AgentName;
  action: string;
  measured: boolean;
  artifact: string | null;
  params: DecoderDesign | null;
  ler: number | null;
  suppression: number | null;
  reward: number | null;
  valid: boolean | null;
  layers: string[] | null;
  gates: boolean | null;
  urls: number | null;
  rtl_hash: string | null;
}

export interface CryoData {
  meta: CryoMeta;
  decoder: Decoder;
  verify: Verify;
  rtl: string;
  waveform: Waveform;
  pareto: Pareto;
  climb: Climb;
  marathon: Marathon;
  research: Research;
  replay: ReplayEvent[];
}
