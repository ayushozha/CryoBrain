import type { CSSProperties, ReactNode } from "react";

// Global keyframes (ported from the design's <style> block). Rendered once.
export function GlobalKeyframes() {
  return (
    <style>{`
      @keyframes cbPulse { 0%,100% { opacity:.35; transform:scale(1); } 50% { opacity:1; transform:scale(1.12); } }
      @keyframes cbReveal { from { opacity:.0001; transform:translateY(26px); } to { opacity:1; transform:none; } }
      @keyframes cbFloat { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-8px); } }
      #cb-root::-webkit-scrollbar { width:0; height:0; }
      ::selection { background:#0a84ff; color:#fff; }
    `}</style>
  );
}

const base: CSSProperties = {
  position: "relative",
  minHeight: "100vh",
  scrollSnapAlign: "start",
};

export function Section({
  label,
  style,
  children,
}: {
  label: string;
  style?: CSSProperties;
  children: ReactNode;
}) {
  return (
    <section data-section data-screen-label={label} style={{ ...base, ...style }}>
      {children}
    </section>
  );
}

// section "kicker" eyebrow text
export function Kicker({ color, children }: { color: string; children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 13,
        fontWeight: 600,
        letterSpacing: ".14em",
        textTransform: "uppercase",
        color,
        marginBottom: 18,
      }}
    >
      {children}
    </div>
  );
}
