import { Section } from "./common";
import { MONO } from "../theme";
import type { Charts } from "../data/derive";
import type { FifoClimbStep } from "../data/types";

const COLS = "2fr 1fr 1fr 1fr 1.2fr";

export function S08Benchmark({ charts, climbFifo }: { charts: Charts | null; climbFifo?: FifoClimbStep[] }) {
  const fifoStart = climbFifo?.[0]?.throughput;
  const fifoEnd = climbFifo?.[climbFifo.length - 1]?.throughput;
  const fifoLine =
    fifoStart != null && fifoEnd != null ? `${fifoStart} → ${fifoEnd}` : "—";

  return (
    <Section label="08 Benchmark" style={{ background: "#fff", color: "#0a0a0c", display: "flex", alignItems: "center" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", width: "100%", padding: "110px 8vw" }}>
        <div style={{ marginBottom: 40, maxWidth: "60ch" }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: "#0a84ff", marginBottom: 14 }}>
            The benchmark
          </div>
          <h2 style={{ fontSize: "clamp(28px,3.8vw,50px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 12px" }}>
            Every design attempt is measured.
          </h2>
          <p style={{ fontSize: 18, color: "#6e6e73", margin: 0 }}>
            Same decode accuracy, same tiny footprint — the swarm searches latency. The honest claim:{" "}
            <strong style={{ color: "#0a0a0c" }}>lower latency at preserved decode behavior.</strong>
          </p>
        </div>
        <div style={{ borderRadius: 18, border: "1px solid rgba(0,0,0,.08)", overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: COLS, padding: "14px 22px", background: "#f5f5f7", fontSize: 11, fontWeight: 700, letterSpacing: ".07em", color: "#6e6e73" }}>
            <span>DESIGN</span>
            <span>MEASURED LER</span>
            <span>AREA µm²</span>
            <span>LATENCY</span>
            <span>STATUS</span>
          </div>
          {(charts?.bench ?? []).map((b) => (
            <div key={b.id} style={{ display: "grid", gridTemplateColumns: COLS, alignItems: "center", padding: "16px 22px", borderTop: "1px solid rgba(0,0,0,.05)", fontSize: 14 }}>
              <span style={{ fontFamily: MONO, color: "#0a0a0c" }}>{b.id}</span>
              <span style={{ fontFamily: MONO, color: "#1d8c3e" }}>{b.ler}</span>
              <span style={{ fontFamily: MONO }}>{b.area}</span>
              <span style={{ fontFamily: MONO }}>{b.latency} cyc</span>
              <span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 11px", borderRadius: 7, background: "rgba(48,209,88,.12)", color: "#1d8c3e", fontSize: 12, fontWeight: 600 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#30d158" }} />
                  {b.status}
                </span>
              </span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 14, marginTop: 18, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 240, padding: "18px 22px", borderRadius: 14, background: "#f5f5f7" }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Repair, not just generation</div>
            <div style={{ fontSize: 13, color: "#6e6e73" }}>Failed designs are rejected with a reason and stored — the swarm repairs them into valid variants.</div>
          </div>
          <div style={{ flex: 1, minWidth: 240, padding: "18px 22px", borderRadius: 14, background: "#0a0c10", color: "#f5f5f7" }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, color: "#64d2ff" }}>FIFO control block</div>
            <div style={{ fontSize: 13, color: "#a1a1aa" }}>
              Same engine, second target: measured throughput climbed{" "}
              <strong style={{ color: "#30d158" }}>{fifoLine}</strong> across measured steps.
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
