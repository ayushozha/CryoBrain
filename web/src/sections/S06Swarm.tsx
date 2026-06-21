import { Section } from "./common";
import { C, MONO } from "../theme";
import { SwarmScene } from "../three/SwarmScene";
import type { SwarmHud } from "../data/derive";
import type { CryoData, ReplayEvent } from "../data/types";

const legend = [
  { c: "#30d158", t: "verified" },
  { c: "#ff453a", t: "rejected" },
  { c: "#0a84ff", t: "measure" },
];

export function S06Swarm({
  data,
  hud,
  onEvent,
  active,
}: {
  data: CryoData | null;
  hud: SwarmHud;
  onEvent: (e: ReplayEvent) => void;
  active: boolean;
}) {
  return (
    <Section label="06 Live swarm" style={{ overflow: "hidden", background: "radial-gradient(120% 90% at 50% 40%, #0b1018 0%, #060608 65%)" }}>
      {data && <SwarmScene data={data} onEvent={onEvent} active={active} />}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          padding: "96px 8vw 56px",
          pointerEvents: "none",
        }}
      >
        <div style={{ maxWidth: 560 }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: C.cyan, marginBottom: 16 }}>
            The live swarm
          </div>
          <h2 style={{ fontSize: "clamp(28px,3.8vw,50px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 14px" }}>
            Eight agents. One measured loop.
          </h2>
          <p style={{ fontSize: 17, color: C.muted, margin: 0 }}>
            Every pulse is a real event. Green is verified, red is rejected — replayed straight from{" "}
            <span style={{ fontFamily: MONO, color: "#9be4ff" }}>event_log.jsonl</span>.
          </p>
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
          <div
            style={{
              pointerEvents: "auto",
              minWidth: 340,
              maxWidth: 460,
              padding: "20px 22px",
              borderRadius: 18,
              background: "rgba(10,12,16,.72)",
              border: `1px solid ${hud.accent}`,
              backdropFilter: "blur(16px)",
              boxShadow: "0 20px 60px rgba(0,0,0,.5)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 9, height: 9, borderRadius: "50%", background: hud.accent, boxShadow: `0 0 10px ${hud.accent}` }} />
                <span style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-.01em", color: "#f5f5f7" }}>{hud.agent}</span>
                <span style={{ fontSize: 12, color: "#8a8a93", fontFamily: MONO }}>{hud.action}</span>
              </div>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                  padding: "4px 9px",
                  borderRadius: 7,
                  background: "rgba(255,255,255,.06)",
                  color: hud.accent,
                }}
              >
                {hud.statusLabel}
              </span>
            </div>
            <div style={{ fontSize: 14, color: "#c8c8cf", fontFamily: MONO, lineHeight: 1.5, marginBottom: 12 }}>{hud.detail}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 11, color: "#6e6e73", fontFamily: MONO }}>design {hud.design}</span>
              {hud.measured && (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: ".08em",
                    textTransform: "uppercase",
                    padding: "3px 8px",
                    borderRadius: 6,
                    background: "rgba(48,209,88,.15)",
                    color: "#30d158",
                  }}
                >
                  measured
                </span>
              )}
            </div>
          </div>
          <div
            style={{
              pointerEvents: "auto",
              display: "flex",
              gap: 18,
              alignItems: "center",
              padding: "12px 18px",
              borderRadius: 14,
              background: "rgba(10,12,16,.6)",
              border: "1px solid rgba(255,255,255,.1)",
              backdropFilter: "blur(12px)",
            }}
          >
            {legend.map((l) => (
              <span key={l.t} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12, color: "#c8c8cf" }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: l.c }} />
                {l.t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}
