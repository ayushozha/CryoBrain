import { Section, Kicker } from "./common";
import { C, MONO } from "../theme";
import type { AgentItem } from "../data/derive";

export function S05Built({ agents, proofFiles }: { agents: AgentItem[]; proofFiles: string[] }) {
  return (
    <Section label="05 What we built" style={{ background: C.bg, display: "flex", alignItems: "center", overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          bottom: "-20%",
          left: "-5%",
          width: "45%",
          height: "70%",
          background: "radial-gradient(circle, rgba(10,132,255,.10), transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "relative", maxWidth: 1180, margin: "0 auto", width: "100%", padding: "120px 8vw" }}>
        <Kicker color={C.cyan}>What we built</Kicker>
        <h2 style={{ fontSize: "clamp(30px,4.2vw,56px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 48px", maxWidth: "22ch" }}>
          A measured multi-agent chip-design swarm.
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 40 }}>
          {agents.map((a) => (
            <div key={a.idx} style={{ padding: 22, borderRadius: 16, background: "rgba(255,255,255,.035)", border: "1px solid rgba(255,255,255,.08)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 12 }}>
                <span style={{ width: 9, height: 9, borderRadius: "50%", background: a.color, boxShadow: `0 0 10px ${a.color}` }} />
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: ".06em", color: "#6e6e73", fontFamily: MONO }}>{a.idx}</span>
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#f5f5f7", marginBottom: 6, letterSpacing: "-.01em" }}>{a.name}</div>
              <div style={{ fontSize: 13, color: "#8a8a93", lineHeight: 1.45 }}>{a.role}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "#6e6e73", letterSpacing: ".08em", textTransform: "uppercase", marginRight: 4 }}>
            Backed by real artifacts
          </span>
          {proofFiles.map((f) => (
            <span
              key={f}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                padding: "8px 13px",
                borderRadius: 9,
                background: "rgba(100,210,255,.08)",
                border: "1px solid rgba(100,210,255,.18)",
                fontSize: 12,
                color: "#9be4ff",
                fontFamily: MONO,
              }}
            >
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#64d2ff" }} />
              {f}
            </span>
          ))}
        </div>
      </div>
    </Section>
  );
}
