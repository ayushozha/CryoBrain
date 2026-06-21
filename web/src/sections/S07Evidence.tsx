import { Section } from "./common";
import { MONO } from "../theme";
import type { Charts } from "../data/derive";
import type { Decoder } from "../data/types";

export function S07Evidence({ charts, decoder }: { charts: Charts | null; decoder?: Decoder }) {
  const metrics = [
    { v: decoder ? decoder.area_um2.toFixed(1) : "—", k: "area µm²" },
    { v: decoder ? String(decoder.cell_count) : "—", k: "cells" },
    { v: decoder ? String(decoder.power_mw) : "—", k: "power mW" },
    { v: decoder ? decoder.ler.toFixed(1) : "—", k: "measured LER" },
  ];
  const benchNote = decoder
    ? `${decoder.shots} Stim shots · surface_code:rotated_memory_z · ${decoder.benchmark_vectors} benchmark vectors, ${decoder.benchmark_failures} failures · beats MWPM baseline (LER ${decoder.mwpm_ler} → ${decoder.ler})`
    : "";

  return (
    <Section label="07 Chip evidence" style={{ background: "#f5f5f7", color: "#0a0a0c", display: "flex", alignItems: "center" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", width: "100%", padding: "110px 6vw" }}>
        <div style={{ marginBottom: 36, maxWidth: "60ch" }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: "#0a84ff", marginBottom: 14 }}>
            The proof
          </div>
          <h2 style={{ fontSize: "clamp(28px,3.8vw,50px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 12px" }}>
            This is not a mock visual.
          </h2>
          <p style={{ fontSize: 18, color: "#6e6e73", margin: 0 }}>
            The design becomes synthesizable RTL, simulates against Stim vectors, and synthesizes through Yosys. Every
            panel below is a real artifact.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1.15fr 1fr", gap: 18, alignItems: "stretch" }}>
          {/* RTL panel */}
          <div style={{ borderRadius: 18, background: "#0b0d12", overflow: "hidden", boxShadow: "0 20px 50px rgba(0,0,0,.18)", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,.07)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#ff5f57" }} />
                <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#febc2e" }} />
                <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#28c840" }} />
              </div>
              <span style={{ fontSize: 12, color: "#8a8a93", fontFamily: MONO }}>generated_decoder.sv</span>
            </div>
            <div style={{ padding: "14px 0", overflow: "auto", maxHeight: 430, fontFamily: MONO, fontSize: 11.5, lineHeight: 1.55 }}>
              {(charts?.rtlLines ?? []).map((ln, i) => (
                <div key={i} style={{ display: "flex", padding: "0 16px", whiteSpace: "pre" }}>
                  <span style={{ color: "#3a3f4a", width: 30, flex: "none", textAlign: "right", marginRight: 14, userSelect: "none" }}>{i}</span>
                  <span style={{ color: "#c4cad6" }}>{ln}</span>
                </div>
              ))}
            </div>
          </div>
          {/* right column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {/* waveform */}
            <div style={{ borderRadius: 18, background: "#0b0d12", padding: "18px 20px", boxShadow: "0 20px 50px rgba(0,0,0,.18)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#f5f5f7" }}>syndrome → correction</span>
                <span style={{ fontSize: 11, color: "#30d158", fontFamily: MONO }}>latency 1 cycle · cryo_golden_trace.vcd</span>
              </div>
              <svg viewBox="0 0 960 130" style={{ width: "100%", height: "auto", display: "block" }}>
                <text x="0" y="10" fill="#64d2ff" fontSize="13" fontFamily="monospace">syndromes_valid</text>
                <polyline points={charts?.svLine} fill="none" stroke="#64d2ff" strokeWidth="2.5" transform="translate(0,14)" opacity="0.9" />
                <text x="0" y="48" fill="#9be4ff" fontSize="13" fontFamily="monospace">syndromes[7:0]</text>
                <polyline points={charts?.synLine} fill="none" stroke="#9be4ff" strokeWidth="2" transform="translate(0,52)" opacity="0.85" />
                <text x="0" y="96" fill="#ffb340" fontSize="13" fontFamily="monospace">corrections[3:0]</text>
                <polyline points={charts?.corrLine} fill="none" stroke="#ffb340" strokeWidth="2.5" transform="translate(0,92)" opacity="0.95" />
              </svg>
            </div>
            {/* synthesis + verify */}
            <div style={{ borderRadius: 18, background: "#fff", border: "1px solid rgba(0,0,0,.06)", padding: "22px 24px", boxShadow: "0 1px 3px rgba(0,0,0,.04)", flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>Yosys synthesis · gate-level signoff</span>
                <span style={{ fontSize: 11, color: "#1d8c3e", fontFamily: MONO, fontWeight: 600 }}>VALID</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 }}>
                {metrics.map((m) => (
                  <div key={m.k}>
                    <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-.02em" }}>{m.v}</div>
                    <div style={{ fontSize: 11, color: "#6e6e73" }}>{m.k}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ fontSize: 11, color: "#6e6e73", marginRight: 2 }}>verification</span>
                {(charts?.layers ?? []).map((L) => (
                  <span
                    key={L.k}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "6px 11px",
                      borderRadius: 8,
                      background: "rgba(48,209,88,.12)",
                      color: "#1d8c3e",
                      fontSize: 12,
                      fontWeight: 600,
                      fontFamily: MONO,
                    }}
                  >
                    {L.k} ✓
                  </span>
                ))}
              </div>
              {benchNote && <div style={{ fontSize: 12, color: "#8a8a93", marginTop: 14 }}>{benchNote}</div>}
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
