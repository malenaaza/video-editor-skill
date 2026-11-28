// The title of a section on screen: an optional label and number, the title, and accent lines that grow out from
// either side. Text comes from `overlays.py chapter`, so this file only draws: never edit it for one video. The idea
// comes from the free Chapter Title template of github.com/reactvideoeditor/remotion-templates (MIT), rewritten for
// this skill's brand and size props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ChapterTitleComposition } from "./ChapterTitle";
//   ... <ChapterTitleComposition />
// Render: npx remotion render src/index.ts ChapterTitle out/chapter.mov --props=chapter-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ChapterTitleProps = {
  title: string;
  number?: string;
  label?: string;
  fontSize?: number;
  accentColor?: string;
  font?: string;
  fontFile?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = { number: "", label: "", fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", seconds: 3, fps: 30, width: 1920, height: 1080 };

export const ChapterTitle: React.FC<ChapterTitleProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const grow = interpolate(frame, [2, 20], [0, 1], { easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pop = spring({ frame: frame - 6, fps, config: { damping: 14, stiffness: 140 } });
  const leave = interpolate(frame, [durationInFrames - 10, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tag = [p.label, p.number].filter(Boolean).join(" ");
  const lineW = p.width * (vertical ? 0.12 : 0.1) * grow;
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", maxWidth: p.width * (vertical ? 0.9 : 0.8),
        backgroundColor: "rgba(20,16,40,0.8)", borderRadius: s * 0.5, padding: `${s * 0.6}px ${s * 0.9}px`, boxShadow: "0 16px 40px rgba(0,0,0,0.35)" }}>
        {tag ? (
          <div style={{ display: "flex", alignItems: "center", gap: s * 0.4, color: p.accentColor, fontSize: s * 0.75, fontWeight: 800,
            textTransform: "uppercase", letterSpacing: s * 0.08, opacity: Math.min(1, pop * 1.5) }}>
            <div style={{ height: s / 14, width: lineW, backgroundColor: p.accentColor, borderRadius: s }} />
            <span>{tag}</span>
            <div style={{ height: s / 14, width: lineW, backgroundColor: p.accentColor, borderRadius: s }} />
          </div>
        ) : null}
        <div style={{ color: "#FFFFFF", fontSize: s * 1.35, fontWeight: 900, textAlign: "center", lineHeight: 1.1, marginTop: tag ? s * 0.25 : 0,
          transform: `translateY(${(1 - pop) * s * 0.5}px)`, opacity: Math.min(1, pop * 1.5) }}>{p.title}</div>
        {!tag ? <div style={{ height: s / 12, width: lineW * 4, backgroundColor: p.accentColor, borderRadius: s, marginTop: s * 0.3 }} /> : null}
      </div>
    </AbsoluteFill>
  );
};

export const ChapterTitleComposition: React.FC = () => (
  <Composition id="ChapterTitle" component={ChapterTitle} durationInFrames={90} fps={30} width={1920} height={1080}
    defaultProps={{ title: "" }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
