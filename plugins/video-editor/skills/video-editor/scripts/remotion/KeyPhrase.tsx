// A short phrase the speaker stresses, big on a marker sweep that draws itself behind the words, then out again.
// Text comes from `overlays.py highlight`, so this file only draws: never edit it for one video. The idea comes from
// the free Text Highlight template of github.com/reactvideoeditor/remotion-templates (MIT), rewritten for this
// skill's brand and size props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { KeyPhraseComposition } from "./KeyPhrase";
//   ... <KeyPhraseComposition />
// Render: npx remotion render src/index.ts KeyPhrase out/keyphrase.mov --props=highlight-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type KeyPhraseProps = {
  text: string;
  top?: number; // 0 = the default place, otherwise the centre line as a fraction of the height
  fontSize?: number;
  accentColor?: string;
  font?: string;
  fontFile?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = { top: 0, fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", seconds: 2.5, fps: 30, width: 1920, height: 1080 };

export const KeyPhrase: React.FC<KeyPhraseProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 170 } });
  const sweep = interpolate(frame, [2, 14], [0, 1], { easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const centre = p.top > 0 ? p.top : vertical ? 0.4 : 0.45;
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", opacity: leave }}>
      <div style={{ position: "absolute", top: p.height * centre, width: p.width * (vertical ? 0.9 : 0.8), display: "flex", justifyContent: "center",
        transform: `translateY(-50%) scale(${0.85 + 0.15 * pop}) rotate(-1.5deg)`, opacity: Math.min(1, pop * 1.5) }}>
        <div style={{ position: "relative", padding: `${s * 0.2}px ${s * 0.6}px`, textAlign: "center" }}>
          <div style={{ position: "absolute", inset: 0, backgroundColor: p.accentColor, borderRadius: s * 0.2, transformOrigin: "left center",
            transform: `scaleX(${sweep})`, boxShadow: "0 12px 30px rgba(0,0,0,0.35)" }} />
          <div style={{ position: "relative", color: "#FFFFFF", fontSize: s * 1.6, fontWeight: 900, lineHeight: 1.1, textTransform: "uppercase",
            textShadow: "0 3px 10px rgba(0,0,0,0.35)" }}>{p.text}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const KeyPhraseComposition: React.FC = () => (
  <Composition id="KeyPhrase" component={KeyPhrase} durationInFrames={75} fps={30} width={1920} height={1080}
    defaultProps={{ text: "" }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
