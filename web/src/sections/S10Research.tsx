import { Section } from "./common";
import { MONO } from "../theme";
import type { Charts, AdoptionStep } from "../data/derive";

export function S10Research({ charts, adoption }: { charts: Charts | null; adoption: AdoptionStep[] }) {
  return (
    <Section label="10 Research adoption" style={{ background: "#f5f5f7", color: "#0a0a0c", display: "flex", alignItems: "center" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", width: "100%", padding: "110px 8vw" }}>
        <div style={{ marginBottom: 44, maxWidth: "60ch" }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: ".14em", textTransform: "uppercase", color: "#0a84ff", marginBottom: 14 }}>
            Research → design
          </div>
          <h2 style={{ fontSize: "clamp(28px,3.8vw,50px)", fontWeight: 600, letterSpacing: "-.03em", lineHeight: 1.05, margin: "0 0 12px" }}>
            It learns from papers, not random mutation.
          </h2>
          <p style={{ fontSize: 18, color: "#6e6e73", margin: 0 }}>
            Live retrieval pulls the QEC-decoder literature into every cycle. Real sources, retrieved this run via Exa:
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 40 }}>
          {(charts?.exa ?? []).map((e) => (
            <a
              key={e.url}
              href={e.url}
              target="_blank"
              rel="noreferrer"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "18px 22px",
                borderRadius: 14,
                background: "#fff",
                border: "1px solid rgba(0,0,0,.06)",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <span style={{ width: 34, height: 34, flex: "none", borderRadius: 9, background: "rgba(10,132,255,.1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>
                📄
              </span>
              <span style={{ flex: 1, fontSize: 15, fontWeight: 500, lineHeight: 1.4 }}>{e.title}</span>
              <span style={{ fontSize: 12, color: "#0a84ff", fontFamily: MONO }}>open ↗</span>
            </a>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap" }}>
          {adoption.map((a) => (
            <div key={a.step} style={{ display: "flex", alignItems: "center" }}>
              <div style={{ padding: "16px 20px", borderRadius: 14, background: a.bg, color: a.fg, minWidth: 120 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase", opacity: 0.7, marginBottom: 5 }}>{a.step}</div>
                <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.3 }}>{a.label}</div>
              </div>
              {a.arrow && <span style={{ margin: "0 10px", color: "#0a84ff", fontSize: 18 }}>→</span>}
            </div>
          ))}
        </div>
        <div style={{ fontSize: 13, color: "#8a8a93", marginTop: 24, maxWidth: "70ch" }}>
          Research retrieval is built and live. The adoption loop is being wired so every ContextPack biases the next
          proposal and tags the verified winner in memory.
        </div>
      </div>
    </Section>
  );
}
