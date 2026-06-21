import { Section } from "./common";
import { C, MONO } from "../theme";
import { HeroScene } from "../three/HeroScene";
import type { Decoder } from "../data/types";

export function S01Hero({ next, decoder }: { next: () => void; decoder?: Decoder }) {
  const badge = decoder
    ? `LER ${decoder.ler.toFixed(1)} · ${decoder.area_um2} µm² · ${decoder.power_mw} mW`
    : "measured decoder — loading…";
  return (
    <Section
      label="01 Hero"
      style={{ overflow: "hidden", background: "radial-gradient(120% 90% at 70% 20%, #0c1018 0%, #060608 60%)" }}
    >
      <HeroScene />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(90deg, rgba(6,6,8,.85) 0%, rgba(6,6,8,.55) 38%, transparent 68%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1100,
          margin: "0 auto",
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "92px 8vw 76px",
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: ".16em",
            textTransform: "uppercase",
            color: C.cyan,
            marginBottom: 18,
          }}
        >
          CryoBrains — The future of chip design
        </div>
        <h1
          style={{
            fontSize: "clamp(34px,5vw,72px)",
            fontWeight: 600,
            letterSpacing: "-.035em",
            lineHeight: 1.03,
            margin: "0 0 22px",
            maxWidth: "13ch",
          }}
        >
          By 2040, every quantum chip needs its own brain.
        </h1>
        <p
          style={{
            fontSize: "clamp(16px,1.85vw,21px)",
            fontWeight: 400,
            color: C.muted,
            maxWidth: "44ch",
            margin: "0 0 32px",
          }}
        >
          Not to run ChatGPT — to survive. We designed the full CryoBrain chip: the AI control brain for the 2040 quantum
          stack. Tonight, the measured loop that builds and verifies its decoder core.
        </p>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <button
            onClick={next}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 9,
              padding: "14px 24px",
              borderRadius: 999,
              border: "none",
              background: C.light,
              color: "#0a0a0c",
              fontSize: 15,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            See the system <span style={{ fontSize: 17 }}>↓</span>
          </button>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 9,
              padding: "14px 22px",
              borderRadius: 999,
              border: "1px solid rgba(255,255,255,.14)",
              background: "rgba(255,255,255,.04)",
              fontSize: 14,
              color: "#c8c8cf",
              fontFamily: MONO,
            }}
          >
            {badge}
          </div>
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: "8vw",
          bottom: 26,
          zIndex: 2,
          fontSize: 11,
          letterSpacing: ".14em",
          textTransform: "uppercase",
          color: "#5a5a63",
          pointerEvents: "none",
        }}
      >
        Concept vision · CryoBrain inside a future quantum stack
      </div>
    </Section>
  );
}
