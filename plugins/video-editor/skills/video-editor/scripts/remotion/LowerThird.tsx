// A name and a role on a bar that slides in from the left and out again, for when someone is introduced. Text comes
// from `overlays.py lowerthird`, so this file only draws: never edit it for one video.
// The idea comes from the free Lower Third template of github.com/reactvideoeditor/remotion-templates (MIT),
// rewritten for this skill's brand and size props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { LowerThirdComposition } from "./LowerThird";
//   ... <LowerThirdComposition />
// Render: npx remotion render src/index.ts LowerThird out/lowerthird.mov --props=lowerthird-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type LowerThirdProps = {
  name: string;
  role?: string;
  top?: number; // 0 = the default place, otherwise the bar's top edge as a fraction of the height
  fontSize?: number;
  accentColor?: string;
  font?: string;
  fontFile?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  role: "", top: 0, fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", seconds: 4, fps: 30,
  width: 1920, height: 1080,
};

export const LowerThird: React.FC<LowerThirdProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const enter = spring({ frame: frame - 2, fps, config: { damping: 16, stiffness: 120 } });
  const leave = interpolate(frame, [durationInFrames - 12, durationInFrames - 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const slide = (1 - enter) * -1.1 + leave * -1.1;           // in from the left, out to the left
  const top = p.top > 0 ? p.top : vertical ? 0.64 : 0.7;
  const left = p.width * (vertical ? 0.06 : 0.07);
  const barW = Math.min(p.width * (vertical ? 0.88 : 0.5), s * 14);
  return (
    <AbsoluteFill style={{ fontFamily: p.font }}>
      <div style={{ position: "absolute", left, top: p.height * top, width: barW,
        transform: `translateX(${slide * (barW + left)}px)`, display: "flex", boxShadow: "0 16px 40px rgba(0,0,0,0.35)",
        borderRadius: s * 0.3, overflow: "hidden" }}>
        <div style={{ width: s * 0.2, backgroundColor: p.accentColor }} />
        <div style={{ flex: 1, backgroundColor: "rgba(20,16,40,0.92)", padding: `${s * 0.3}px ${s * 0.55}px` }}>
          <div style={{ color: "#FFFFFF", fontSize: s * 0.95, fontWeight: 800, lineHeight: 1.1 }}>{p.name}</div>
          {p.role ? (
            <div style={{ color: p.accentColor, fontSize: s * 0.6, fontWeight: 700, marginTop: s * 0.1,
              opacity: interpolate(frame, [8, 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
              {p.role}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const LowerThirdComposition: React.FC = () => (
  <Composition id="LowerThird" component={LowerThird} durationInFrames={120} fps={30} width={1920} height={1080}
    defaultProps={{ name: "" }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
