import { Section } from "./common";
import { C, MONO } from "../theme";
import type { Charts } from "../data/derive";
import type { Marathon } from "../data/types";

export function S11Memory({ charts, marathon }: { charts: Charts | null; marathon?: Marathon }) {
  const dots = charts?.fifoDots ?? [];
  const startTp = dots[0]?.tp;
  const endTp = dots[dots.length - 1]?.tp;
  // measured improvement percentage from real throughput numbers
  const pct = startTp && endTp && startTp > 0 ? Math.round(((endTp - startTp) / startTp) * 100) : null;
  const completed = marathon?.completed ?? 0;
  const status = marathon?.status ?? "—";

  return (
    <Section label="11 Memory & improvement" style={{ background: C.bg, display: "flex", alignItems: "center", overflow: "hidden" }}>
      <div style={{ position: "absolute", bottom: 0, right: 0, width: "45%", height: "60%", background: "radial-gradient(circle at 70% 70%, rgba(48,209,88,.10), transparent 70%)", pointerEvents: "none" }} />
      <div style={{ position: "relative", maxWidth: 1180, margin: "0 auto", width: "100%", padding: "110px 8vw" }}>
        <div style={{ marginBottom: 44, maxWidth: "60ch" }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: C.cyan, marginBottom: 14 }}>
            Memory & compounding
          </div>
          <h2 style={{ fontSize: "clamp(28px,3.8vw,50px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 12px" }}>
            It remembers what worked — and what failed.
          </h2>
          <p style={{ fontSize: 18, color: C.muted, margin: 0 }}>
            Verified winners and rejected designs both become reusable knowledge. The proof it compounds: a {completed}-cycle
            measured marathon.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 18 }}>
          {/* FIFO climb chart */}
          <div style={{ borderRadius: 18, background: "rgba(255,255,255,.03)", border: "1px solid rgba(255,255,255,.08)", padding: "24px 28px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "#f5f5f7" }}>Measured improvement — FIFO throughput</span>
              {pct != null && <span style={{ fontSize: 13, color: "#30d158", fontFamily: MONO, fontWeight: 600 }}>+{pct}%</span>}
            </div>
            <svg viewBox="0 0 300 140" style={{ width: "100%", height: "auto", display: "block" }}>
              <line x1="24" y1="120" x2="290" y2="120" stroke="rgba(255,255,255,.12)" />
              <polyline points={charts?.fifoPath} fill="none" stroke="#30d158" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              {dots.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r="5" fill="#060608" stroke="#30d158" strokeWidth="2.5" />
              ))}
              {startTp != null && <text x="24" y="136" fill="#6e6e73" fontSize="11" fontFamily="monospace">{startTp}</text>}
              {endTp != null && <text x="252" y="136" fill="#30d158" fontSize="11" fontFamily="monospace">{endTp}</text>}
            </svg>
            <div style={{ fontSize: 12, color: "#6e6e73", marginTop: 6 }}>measured_fifo_climb.json · Verilator throughput</div>
          </div>
          {/* marathon + memory ab */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div style={{ borderRadius: 18, background: "linear-gradient(160deg,#0a1a10,#0a0c10)", border: "1px solid rgba(48,209,88,.2)", padding: "24px 28px" }}>
              <div style={{ fontSize: 42, fontWeight: 600, letterSpacing: "-.03em", color: "#30d158", lineHeight: 1 }}>
                {completed}
                <span style={{ fontSize: 18, color: "#a1a1aa", fontWeight: 400 }}> / {marathon?.requested ?? completed} cycles</span>
              </div>
              <div style={{ fontSize: 13, color: "#a1a1aa", margin: "8px 0 16px", fontFamily: MONO }}>status: {status}</div>
              <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                {(charts?.cycles ?? []).map((c) => (
                  <span key={c.cycle} style={{ width: 9, height: 18, borderRadius: 2, background: "#30d158", opacity: 0.8 }} />
                ))}
              </div>
            </div>
            <div style={{ borderRadius: 18, background: "rgba(255,255,255,.03)", border: "1px solid rgba(255,255,255,.08)", padding: "18px 22px" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#f5f5f7", marginBottom: 5 }}>Memory A/B — honest status</div>
              <div style={{ fontSize: 13, color: "#8a8a93", lineHeight: 1.5 }}>
                Wiring proven (with-memory vs without both verified). Multi-step slope is the next measured milestone — we
                don't claim it yet.
              </div>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
