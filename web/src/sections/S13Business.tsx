import { Section, Kicker } from "./common";
import { C, MONO } from "../theme";
import type { WedgeItem } from "../data/derive";

export function S13Business({ wedge }: { wedge: WedgeItem[] }) {
  return (
    <Section label="13 Business" style={{ background: "#f5f5f7", color: "#0a0a0c", display: "flex", alignItems: "center" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", width: "100%", padding: "110px 8vw" }}>
        <div style={{ marginBottom: 44, maxWidth: "60ch" }}>
          <Kicker color="#0a84ff">The wedge</Kicker>
          <h2 style={{ fontSize: "clamp(28px,3.8vw,50px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 12px" }}>
            Improve any hardware design you can verify.
          </h2>
          <p style={{ fontSize: 18, color: "#6e6e73", margin: 0 }}>
            AI labs and EDA teams need measured environments for hardware agents. Verification is the immediate pain;
            quantum decoder / control design is the moonshot.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 18 }}>
          {wedge.map((w) => (
            <div key={w.num} style={{ padding: 28, borderRadius: 20, background: w.bg, color: w.fg, border: w.bg === "#fff" ? "1px solid rgba(0,0,0,.06)" : "none", minHeight: 200, display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: ".1em", fontFamily: MONO, opacity: 0.6, marginBottom: 16 }}>{w.num}</div>
              <div style={{ fontSize: 19, fontWeight: 600, letterSpacing: "-.01em", lineHeight: 1.2, marginBottom: 12 }}>{w.title}</div>
              <div style={{ fontSize: 14, opacity: 0.85, lineHeight: 1.5 }}>{w.note}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 13, color: "#8a8a93", marginTop: 24, maxWidth: "70ch" }}>
          The beachhead is verifiable hardware-design environments. CryoBrain starts with the NPU brain inside future
          quantum chips — not selling quantum chips tomorrow.
        </p>
      </div>
      <span style={{ position: "absolute", bottom: 22, right: 22, fontSize: 11, color: C.muted3, fontFamily: MONO }} />
    </Section>
  );
}
