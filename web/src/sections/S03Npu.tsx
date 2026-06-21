import { Section, Kicker } from "./common";
import { C, MONO } from "../theme";
import type { NpuItem } from "../data/derive";

export function S03Npu({ npu }: { npu: NpuItem[] }) {
  return (
    <Section label="03 NPU trend" style={{ background: C.bg, display: "flex", alignItems: "center", overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          top: "-20%",
          right: "-10%",
          width: "50%",
          height: "80%",
          background: "radial-gradient(circle, rgba(10,132,255,.10), transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "relative", maxWidth: 1180, margin: "0 auto", width: "100%", padding: "120px 8vw" }}>
        <Kicker color={C.cyan}>The pattern</Kicker>
        <h2 style={{ fontSize: "clamp(30px,4.2vw,56px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 14px", maxWidth: "20ch" }}>
          The NPU is already here.
          <br />
          We apply it to quantum control.
        </h2>
        <p style={{ fontSize: 19, color: C.muted, maxWidth: "50ch", margin: "0 0 64px" }}>
          Every modern chip added a neural engine because CPUs and GPUs are the wrong substrate for real-time, low-power
          AI. The quantum stack will need the same — one step further down, inside the fridge.
        </p>
        <div style={{ display: "flex", alignItems: "stretch", gap: 0, position: "relative" }}>
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 34,
              height: 2,
              background: "linear-gradient(90deg, rgba(255,255,255,.12) 0%, rgba(100,210,255,.5) 100%)",
            }}
          />
          {npu.map((n) => (
            <div key={n.name} style={{ flex: 1, position: "relative", paddingRight: 18 }}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: n.dot,
                  border: "3px solid #060608",
                  boxShadow: "0 0 0 1px rgba(255,255,255,.15)",
                  marginBottom: 30,
                  position: "relative",
                  zIndex: 2,
                }}
              />
              <div style={{ fontSize: 12, fontWeight: 600, letterSpacing: ".08em", color: "#6e6e73", marginBottom: 8, fontFamily: MONO }}>
                {n.year}
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#f5f5f7", marginBottom: 6, letterSpacing: "-.01em" }}>{n.name}</div>
              <div style={{ fontSize: 13, color: "#8a8a93", lineHeight: 1.45 }}>{n.note}</div>
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}
