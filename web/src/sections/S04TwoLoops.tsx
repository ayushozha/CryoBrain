import { Section } from "./common";
import { MONO } from "../theme";

const fastLoop = ["QPU", "syndrome stream", "CryoBrain NPU", "corrections"];
const slowLoop = ["research", "design", "measure", "improve"];

export function S04TwoLoops() {
  return (
    <Section label="04 Two loops" style={{ background: "#f5f5f7", color: "#0a0a0c", display: "flex", alignItems: "center" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto", width: "100%", padding: "120px 8vw" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: "#0a84ff", marginBottom: 16 }}>
            The concept
          </div>
          <h2 style={{ fontSize: "clamp(32px,4.6vw,60px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.04, margin: 0 }}>
            CryoBrain has two loops.
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28 }}>
          <div style={{ padding: 40, borderRadius: 24, background: "linear-gradient(160deg,#0a0c10,#121826)", color: "#f5f5f7", position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", top: "-30%", right: "-20%", width: "60%", height: "80%", background: "radial-gradient(circle, rgba(100,210,255,.18), transparent 70%)" }} />
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 999, background: "rgba(255,214,10,.14)", color: "#ffd60a", fontSize: 11, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 24 }}>
              Vision · the destination
            </div>
            <h3 style={{ fontSize: 24, fontWeight: 600, margin: "0 0 8px", letterSpacing: "-.02em" }}>Fast loop — real-time chip brain</h3>
            <p style={{ fontSize: 15, color: "#a1a1aa", margin: "0 0 28px" }}>Inside the fridge, sub-microsecond, decode-and-correct before errors accumulate.</p>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", fontSize: 13, fontFamily: MONO }}>
              {fastLoop.map((s, i) => (
                <span key={s} style={{ display: "contents" }}>
                  <span style={{ padding: "9px 13px", borderRadius: 10, background: i === 2 ? "rgba(100,210,255,.16)" : "rgba(255,255,255,.06)", color: i === 2 ? "#64d2ff" : undefined }}>
                    {s}
                  </span>
                  {i < fastLoop.length - 1 && <span style={{ color: "#64d2ff" }}>→</span>}
                </span>
              ))}
            </div>
          </div>
          <div style={{ padding: 40, borderRadius: 24, background: "#fff", border: "1px solid rgba(0,0,0,.06)", boxShadow: "0 1px 3px rgba(0,0,0,.04)", position: "relative", overflow: "hidden" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 999, background: "rgba(48,209,88,.14)", color: "#1d8c3e", fontSize: 11, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 24 }}>
              Built · shipping tonight
            </div>
            <h3 style={{ fontSize: 24, fontWeight: 600, margin: "0 0 8px", letterSpacing: "-.02em", color: "#0a0a0c" }}>Slow loop — the swarm improves the next design</h3>
            <p style={{ fontSize: 15, color: "#6e6e73", margin: "0 0 28px" }}>Agents research, propose, generate RTL, measure, verify, score, remember — then do it again, better.</p>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: 13, fontFamily: MONO, color: "#0a0a0c" }}>
              {slowLoop.map((s, i) => (
                <span key={s} style={{ display: "contents" }}>
                  <span style={{ padding: "9px 12px", borderRadius: 10, background: i === 3 ? "rgba(48,209,88,.16)" : "#f0f0f2", color: i === 3 ? "#1d8c3e" : undefined }}>
                    {s}
                  </span>
                  {i < slowLoop.length - 1 && <span style={{ color: "#0a84ff" }}>→</span>}
                </span>
              ))}
            </div>
          </div>
        </div>
        <p style={{ textAlign: "center", fontSize: 15, color: "#6e6e73", margin: "36px 0 0" }}>
          The fast loop is the destination. <strong style={{ color: "#0a0a0c" }}>The slow loop is what we built — and measured.</strong>
        </p>
      </div>
    </Section>
  );
}
