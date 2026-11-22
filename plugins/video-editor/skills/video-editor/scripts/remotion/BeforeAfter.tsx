// A before and an after: the before shows, then the after sweeps in over it from the left behind an accent line as
// the speaker says it. Each side is an image or a text (a weak prompt and a good one, a draft and the AI's version).
// The reveal time comes from `overlays.py beforeafter`, so this file only draws: never edit it for one video.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { BeforeAfterComposition } from "./BeforeAfter";
//   ... <BeforeAfterComposition />
// Render: npx remotion render src/index.ts BeforeAfter out/beforeafter.mov --props=beforeafter-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type BeforeAfterSide = { label: string; text: string; image: string };

export type BeforeAfterProps = {
  before: BeforeAfterSide;
  after: BeforeAfterSide;
  reveal: number;
  revealFrames: number;
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
  fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", background: "#1B1033",
  background2: "#0E2A47", seconds: 6, fps: 30, width: 1920, height: 1080,
};

const Panel: React.FC<{ side: BeforeAfterSide; s: number; after: boolean; accent: string }> = ({ side, s, after, accent }) => (
  <AbsoluteFill style={{ backgroundColor: after ? "#FFFFFF" : "#E9E9EF", alignItems: "center", justifyContent: "center" }}>
    {side.image ? (
      <Img src={staticFile(side.image)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    ) : (
      <div style={{ padding: s, fontSize: s * 0.95, fontWeight: 700, lineHeight: 1.3, textAlign: "center",
        color: after ? "#1A1A1A" : "#6A6A75", whiteSpace: "pre-wrap" }}>
        {side.text}
      </div>
    )}
    {side.label ? (
      <div style={{ position: "absolute", top: s * 0.5, left: s * 0.5, padding: `${s * 0.15}px ${s * 0.5}px`, borderRadius: s,
        backgroundColor: after ? accent : "#55555F", color: "#FFFFFF", fontSize: s * 0.55, fontWeight: 800 }}>
        {side.label}
      </div>
    ) : null}
  </AbsoluteFill>
);

export const BeforeAfter: React.FC<BeforeAfterProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const w = vertical ? p.width * 0.9 : p.width * 0.78;
  const h = vertical ? p.height * 0.6 : p.height * 0.8;
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 140 } });
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const wipe = interpolate(frame, [p.reveal, p.reveal + p.revealFrames], [0, 1],
    { easing: Easing.inOut(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const over = p.background === "transparent";
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center",
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div style={{ position: "relative", width: w, height: h, borderRadius: s * 0.5, overflow: "hidden",
        boxShadow: "0 30px 80px rgba(0,0,0,0.35)", transform: `scale(${0.92 + 0.08 * enter})`, opacity: Math.min(1, enter * 1.4) * leave }}>
        <Panel side={p.before} s={s} after={false} accent={p.accentColor} />
        <AbsoluteFill style={{ clipPath: `inset(0 ${(1 - wipe) * 100}% 0 0)` }}>
          <Panel side={p.after} s={s} after accent={p.accentColor} />
        </AbsoluteFill>
        {wipe > 0 && wipe < 1 ? (
          <div style={{ position: "absolute", top: 0, bottom: 0, left: `calc(${wipe * 100}% - ${s / 10}px)`,
            width: s / 5, backgroundColor: p.accentColor, boxShadow: `0 0 ${s}px ${p.accentColor}` }} />
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const BeforeAfterComposition: React.FC = () => (
  <Composition id="BeforeAfter" component={BeforeAfter} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ before: { label: "", text: "", image: "" }, after: { label: "", text: "", image: "" }, reveal: 30, revealFrames: 18 }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
