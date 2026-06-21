import { Section } from "./common";
import { C } from "../theme";

export function S14Close() {
  return (
    <Section
      label="14 Close"
      style={{
        background: "radial-gradient(120% 90% at 50% 40%, #0b1018 0%, #060608 65%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      <div style={{ maxWidth: 820, padding: "120px 8vw" }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, margin: "0 auto 28px", background: "linear-gradient(135deg,#64d2ff,#0a84ff)", boxShadow: "0 0 28px rgba(10,132,255,.6)" }} />
        <h2 style={{ fontSize: "clamp(30px,4.4vw,58px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.08, margin: "0 0 22px" }}>
          CryoBrain is the AI hardware lab for the brain inside future quantum chips.
        </h2>
        <p style={{ fontSize: 18, color: C.muted, margin: "0 auto", maxWidth: "52ch" }}>
          Agents research, design, generate RTL, measure, verify, remember, and improve — every step backed by real
          artifacts.
        </p>
      </div>
    </Section>
  );
}
