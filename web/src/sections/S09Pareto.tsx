import { Section, Kicker } from "./common";
import { C } from "../theme";
import type { Charts } from "../data/derive";
import type { Pareto } from "../data/types";

export function S09Pareto({ charts, pareto }: { charts: Charts | null; pareto?: Pareto }) {
  const blurb = pareto
    ? `${pareto.count} measured designs, ${pareto.frontier_count} on the frontier. The decoder cluster sits in the ideal corner — perfect decode at the smallest footprint — while the FIFO target sweeps the tradeoff.`
    : "Measured designs on the accuracy ↔ hardware frontier.";

  return (
    <Section label="09 Pareto frontier" style={{ background: C.bg, display: "flex", alignItems: "center", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: "10%", left: "5%", width: "40%", height: "60%", background: "radial-gradient(circle, rgba(48,209,88,.08), transparent 70%)", pointerEvents: "none" }} />
      <div style={{ position: "relative", maxWidth: 1180, margin: "0 auto", width: "100%", padding: "110px 8vw", display: "grid", gridTemplateColumns: "1fr 1.1fr", gap: 56, alignItems: "center" }}>
        <div>
          <Kicker color={C.cyan}>The frontier</Kicker>
          <h2 style={{ fontSize: "clamp(28px,3.6vw,48px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.06, margin: "0 0 18px" }}>
            The accuracy ↔ hardware frontier.
          </h2>
          <p style={{ fontSize: 17, color: C.muted, margin: "0 0 28px" }}>{blurb}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, color: "#c8c8cf" }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#30d158", boxShadow: "0 0 8px #30d158" }} />
              Decoder — verified, on frontier (LER 0)
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, color: "#c8c8cf" }}>
              <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#ffb340" }} />
              FIFO — explored tradeoff points
            </div>
          </div>
        </div>
        <div style={{ borderRadius: 18, background: "rgba(255,255,255,.03)", border: "1px solid rgba(255,255,255,.08)", padding: "26px 28px" }}>
          <svg viewBox="0 0 320 280" style={{ width: "100%", height: "auto", display: "block", overflow: "visible" }}>
            <line x1="34" y1="8" x2="34" y2="244" stroke="rgba(255,255,255,.14)" strokeWidth="1" />
            <line x1="34" y1="244" x2="316" y2="244" stroke="rgba(255,255,255,.14)" strokeWidth="1" />
            <text x="34" y="266" fill="#6e6e73" fontSize="11" fontFamily="monospace">hardware area µm² (log) →</text>
            <text x="20" y="10" fill="#6e6e73" fontSize="11" fontFamily="monospace" transform="rotate(-90 20 10) translate(-150 0)">accuracy →</text>
            <g transform="translate(34,8) scale(2.82,2.36)">
              {(charts?.paretoFifo ?? []).map((p, i) => (
                <circle key={`f${i}`} cx={p.cx} cy={p.cy} r="2.4" fill="#ffb340" opacity="0.9" />
              ))}
              {(charts?.paretoDec ?? []).map((p, i) => (
                <circle key={`d${i}`} cx={p.cx} cy={p.cy} r="2.2" fill="#30d158" opacity="0.85" />
              ))}
            </g>
            <circle cx="51" cy="27" r="9" fill="none" stroke="#30d158" strokeWidth="1.4" opacity="0.7" />
            <text x="64" y="24" fill="#30d158" fontSize="11" fontFamily="monospace">ideal corner</text>
            <text x="64" y="37" fill="#6e6e73" fontSize="10" fontFamily="monospace">LER 0 · 6 µm²</text>
          </svg>
          <div style={{ fontSize: 12, color: "#6e6e73", marginTop: 14, lineHeight: 1.5 }}>
            Today's run proves the loop and the gate. Next push: more L2-valid variants to fill the frontier.
          </div>
        </div>
      </div>
    </Section>
  );
}
