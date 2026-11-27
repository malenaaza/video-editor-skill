// One number out of a maximum (usually a percentage) as a ring that fills while the number counts up, written the
// Spanish way. Times come from `overlays.py ring`, so this file only draws: never edit it for one video. The idea
// comes from the free Circular Progress template of github.com/reactvideoeditor/remotion-templates (MIT),
// rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ProgressRingComposition } from "./ProgressRing";
//   ... <ProgressRingComposition />
// Render: npx remotion render src/index.ts ProgressRing out/ring.mov --props=ring-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ProgressRingProps = {
  value: number;
  max?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  label?: string;
  frame?: number;
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
  max: 100, decimals: 0, prefix: "", suffix: " %", label: "", frame: 10, fontSize: 54, accentColor: "#FF4F8B",
  font: "sans-serif", fontFile: "", background: "#1B1033", background2: "#0E2A47", seconds: 4, fps: 30, width: 1920, height: 1080,
};

const formatEs = (value: number, decimals: number) => {
  const [whole, part] = value.toFixed(decimals).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return part ? `${grouped},${part}` : grouped;
};

export const ProgressRing: React.FC<ProgressRingProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const over = p.background === "transparent";
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pop = spring({ frame: frame - p.frame, fps, config: { damping: 14, stiffness: 140 } });
  const fill = interpolate(frame, [p.frame, p.frame + Math.round(fps * 1.1)], [0, p.value / p.max],
    { easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const size = s * 7;
  const stroke = s * 0.45;
  const r = size / 2 - stroke / 2;
  const circ = 2 * Math.PI * r;
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div style={{ position: "relative", width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center",
        flexDirection: "column", transform: `scale(${0.6 + 0.4 * pop})`, opacity: Math.min(1, pop * 1.5) }}>
        <svg width={size} height={size} style={{ position: "absolute", transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill={over ? "rgba(20,16,40,0.85)" : "none"} stroke="rgba(255,255,255,0.2)" strokeWidth={stroke} />
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={p.accentColor} strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={circ * (1 - fill)} />
        </svg>
        <div style={{ color: "#FFFFFF", fontSize: s * 1.9, fontWeight: 900, lineHeight: 1, whiteSpace: "nowrap" }}>
          {p.prefix}{formatEs(fill * p.max, p.decimals)}{p.suffix}
        </div>
        {p.label ? <div style={{ color: p.accentColor, fontSize: s * 0.6, fontWeight: 700, marginTop: s * 0.2 }}>{p.label}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

export const ProgressRingComposition: React.FC = () => (
  <Composition id="ProgressRing" component={ProgressRing} durationInFrames={120} fps={30} width={1920} height={1080}
    defaultProps={{ value: 0 }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
