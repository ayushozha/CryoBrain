import { Section } from "./common";
import { C, MONO } from "../theme";
import { ChipScene } from "../three/ChipScene";
import type { SpecRow } from "../data/derive";

export function S12Chip({ chipSpec }: { chipSpec: SpecRow[] }) {
  return (
    <Section label="12 2040 chip concept" style={{ overflow: "hidden", background: "radial-gradient(120% 90% at 35% 50%, #0c1018 0%, #060608 65%)" }}>
      <ChipScene />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(90deg, rgba(6,6,8,.88) 0%, rgba(6,6,8,.6) 36%, transparent 60%)",
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "relative", zIndex: 2, minHeight: "100vh", display: "flex", alignItems: "center", padding: "96px 8vw", pointerEvents: "none" }}>
        <div style={{ maxWidth: 370 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 999, background: "rgba(255,214,10,.14)", color: "#ffd60a", fontSize: 11, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 22 }}>
            2040 system concept
          </div>
          <h2 style={{ fontSize: "clamp(28px,3.6vw,48px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.06, margin: "0 0 16px" }}>
            From decoder block to quantum control NPU.
          </h2>
          <p style={{ fontSize: 17, color: C.muted, margin: "0 0 28px" }}>
            We designed the full chip: a QPU array with a co-located CryoBrain NPU, local memory, control lines, and a
            classical interface — all inside the cryostat package.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, pointerEvents: "auto" }}>
            {chipSpec.map((s) => (
              <div key={s.k} style={{ display: "flex", justifyContent: "space-between", gap: 16, padding: "11px 0", borderBottom: "1px solid rgba(255,255,255,.08)" }}>
                <span style={{ fontSize: 13, color: "#8a8a93" }}>{s.k}</span>
                <span style={{ fontSize: 13, color: "#f5f5f7", fontFamily: MONO, textAlign: "right" }}>{s.v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}
