import { C, MONO } from "../theme";
import type { Marathon } from "../data/types";

export function TopNav({ era, marathon }: { era: string; marathon?: Marathon }) {
  const status = marathon
    ? `${era} · ${marathon.completed}-cycle marathon · ${marathon.status}`
    : `${era} · awaiting run`;
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "20px 32px",
        pointerEvents: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, pointerEvents: "auto" }}>
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 6,
            background: "linear-gradient(135deg,#64d2ff,#0a84ff)",
            boxShadow: "0 0 18px rgba(10,132,255,.6)",
          }}
        />
        <span style={{ fontSize: 16, fontWeight: 600, letterSpacing: "-.01em" }}>CryoBrains</span>
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "7px 13px",
          borderRadius: 999,
          background: "rgba(255,255,255,.06)",
          border: "1px solid rgba(255,255,255,.10)",
          backdropFilter: "blur(12px)",
          pointerEvents: "auto",
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: C.green,
            boxShadow: `0 0 8px ${C.green}`,
            animation: "cbPulse 2.4s ease-in-out infinite",
          }}
        />
        <span style={{ fontSize: 12, fontWeight: 500, color: "#c8c8cf", fontFamily: MONO }}>{status}</span>
      </div>
    </div>
  );
}

export function DotNav({ active, goTo, count }: { active: number; goTo: (i: number) => void; count: number }) {
  return (
    <div
      style={{
        position: "fixed",
        right: 22,
        top: "50%",
        transform: "translateY(-50%)",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        gap: 11,
      }}
    >
      {Array.from({ length: count }, (_, i) => {
        const on = i === active;
        return (
          <button
            key={i}
            onClick={() => goTo(i)}
            title={String(i + 1).padStart(2, "0")}
            style={{
              width: on ? 26 : 9,
              height: 9,
              padding: 0,
              border: "none",
              cursor: "pointer",
              borderRadius: 999,
              transition: "all .4s cubic-bezier(.22,1,.36,1)",
              background: on ? "linear-gradient(90deg,#64d2ff,#0a84ff)" : "rgba(255,255,255,.28)",
              boxShadow: on ? "0 0 12px rgba(10,132,255,.7)" : "none",
            }}
          />
        );
      })}
    </div>
  );
}
