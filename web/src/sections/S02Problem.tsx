import { Section } from "./common";
import { MONO } from "../theme";

const loopTags = ["correct", "synthesizes", "area · latency · power", "verified"];

export function S02Problem() {
  return (
    <Section label="02 Why AI RTL isn't enough" style={{ background: "#f5f5f7", color: "#0a0a0c", display: "flex", alignItems: "center" }}>
      <div
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          width: "100%",
          padding: "120px 8vw",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 72,
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: "#0a84ff", marginBottom: 18 }}>
            The problem
          </div>
          <h2 style={{ fontSize: "clamp(32px,4.4vw,58px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 24px" }}>
            AI writing RTL is useful.
            <br />
            It is not enough.
          </h2>
          <p style={{ fontSize: 19, color: "#6e6e73", maxWidth: "42ch", margin: 0 }}>
            An LLM can emit Verilog. But hardware only counts when it is measured, verified, synthesized, and improved
            against hidden cases — not when it merely looks plausible.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div
            style={{
              display: "flex",
              gap: 16,
              padding: "22px 24px",
              borderRadius: 18,
              background: "#fff",
              border: "1px solid rgba(0,0,0,.06)",
              boxShadow: "0 1px 3px rgba(0,0,0,.04)",
            }}
          >
            <div style={{ fontSize: 22 }}>⚠</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>"AI writes Verilog"</div>
              <div style={{ fontSize: 15, color: "#6e6e73" }}>Plausible text. No proof it is correct, synthesizable, or in budget.</div>
            </div>
          </div>
          <div
            style={{
              padding: 24,
              borderRadius: 18,
              background: "linear-gradient(135deg,#0a0c10,#101620)",
              color: "#f5f5f7",
              border: "1px solid rgba(100,210,255,.2)",
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".12em", textTransform: "uppercase", color: "#64d2ff", marginBottom: 14 }}>
              The loop that counts
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, fontSize: 13, fontFamily: MONO }}>
              {loopTags.map((t) => (
                <span key={t} style={{ padding: "6px 11px", borderRadius: 8, background: "rgba(255,255,255,.06)" }}>
                  {t}
                </span>
              ))}
              <span style={{ padding: "6px 11px", borderRadius: 8, background: "rgba(48,209,88,.16)", color: "#30d158" }}>
                improves measured behavior
              </span>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
