// Two to five items appearing one by one as the speaker says them, each with a number that turns into a tick.
// An item without text is just its number (1, 2, 3). Times come from `overlays.py checklist`, so this file only
// draws: never edit it for one video.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ChecklistComposition } from "./Checklist";
//   ... <ChecklistComposition />
// Render: npx remotion render src/index.ts Checklist out/checklist.mov --props=checklist-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ChecklistItem = { text: string; frame: number };

export type ChecklistProps = {
  items: ChecklistItem[];
  title?: string;
  fontSize?: number;
  accentColor?: string;
  font?: string;
  fontFile?: string;
  background?: string;
  background2?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  title: "", fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", background: "#1B1033",
  background2: "#0E2A47", seconds: 6, fps: 30, width: 1920, height: 1080,
};

export const Checklist: React.FC<ChecklistProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const over = p.background === "transparent";
  const cardW = Math.min(p.width * (vertical ? 0.86 : 0.55), s * 16);
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div style={{ width: cardW, display: "flex", flexDirection: "column", gap: s * 0.45 }}>
        {p.title ? (
          <div style={{ color: "#FFFFFF", fontSize: s * 1.05, fontWeight: 800, textAlign: "center", marginBottom: s * 0.2,
            textShadow: over ? "0 4px 16px rgba(0,0,0,0.5)" : "none",
            opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" }) }}>
            {p.title}
          </div>
        ) : null}
        {p.items.map((it, i) => {
          if (frame < it.frame) return <div key={i} style={{ height: s * 1.5 }} />;
          const pop = spring({ frame: frame - it.frame, fps, config: { damping: 16, stiffness: 160 } });
          const t0 = it.frame + (it.text ? Math.round(fps * 0.5) : 4);
          const tick = interpolate(frame, [t0, t0 + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const badge = s * 1.2;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: s * 0.5, backgroundColor: "#FFFFFF",
              borderRadius: s * 0.5, padding: `${s * 0.3}px ${s * 0.5}px`, boxShadow: "0 16px 40px rgba(0,0,0,0.30)",
              borderLeft: `${s / 8}px solid ${p.accentColor}`, transform: `translateY(${(1 - pop) * s * 0.8}px)`, opacity: pop,
              justifyContent: "flex-start" }}>
              <div style={{ width: badge, height: badge, borderRadius: "50%", flexShrink: 0, position: "relative",
                backgroundColor: p.accentColor, color: "#FFFFFF", fontSize: s * 0.75, fontWeight: 800,
                display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ opacity: 1 - tick }}>{i + 1}</span>
                <svg viewBox="0 0 24 24" width={badge * 0.6} height={badge * 0.6} style={{ position: "absolute", opacity: tick }}>
                  <path d="M4 12.5 L9.5 18 L20 6.5" fill="none" stroke="#FFFFFF" strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div style={{ fontSize: s * 0.8, fontWeight: 700, color: "#2A2A33" }}>{it.text || String(i + 1)}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const ChecklistComposition: React.FC = () => (
  <Composition id="Checklist" component={Checklist} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ items: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
