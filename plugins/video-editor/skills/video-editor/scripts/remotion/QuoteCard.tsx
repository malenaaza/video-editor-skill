// A quotation with its author: a big accent-coloured quotation mark, the words fading in one by one as the speaker
// reads them out, then the author. Text and times come from `overlays.py quote`, so this file only draws: never
// edit it for one video. The idea comes from the free Quote Card template of
// github.com/reactvideoeditor/remotion-templates (MIT), rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { QuoteCardComposition } from "./QuoteCard";
//   ... <QuoteCardComposition />
// Render: npx remotion render src/index.ts QuoteCard out/quote.mov --props=quote-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type QuoteCardProps = {
  quote: string;
  author?: string;
  authorFrame?: number;
  wordFrames?: number; // over how many frames the words appear
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
  author: "", authorFrame: 60, wordFrames: 60, fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "",
  background: "#1B1033", background2: "#0E2A47", seconds: 6, fps: 30, width: 1920, height: 1080,
};

export const QuoteCard: React.FC<QuoteCardProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const over = p.background === "transparent";
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const words = p.quote.split(/\s+/).filter(Boolean);
  const start = Math.round(fps * 0.4);
  const mark = spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  const authorIn = interpolate(frame, [p.authorFrame, p.authorFrame + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div style={{ width: p.width * (vertical ? 0.84 : 0.66), textAlign: "center", ...(over ? { backgroundColor: "rgba(20,16,40,0.85)",
        borderRadius: s * 0.5, padding: `${s * 0.6}px ${s * 0.8}px` } : {}) }}>
        <div style={{ color: p.accentColor, fontSize: s * 3.2, fontWeight: 900, lineHeight: 0.8, height: s * 1.4,
          transform: `scale(${0.5 + 0.5 * mark})`, opacity: Math.min(1, mark * 1.5) }}>“</div>
        <div style={{ color: "#FFFFFF", fontSize: s * (words.length > 18 ? 0.85 : 1.1), fontWeight: 700, lineHeight: 1.25 }}>
          {words.map((w, i) => {
            const at = start + Math.round((i / Math.max(1, words.length)) * p.wordFrames);
            const o = interpolate(frame, [at, at + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return <span key={i} style={{ opacity: o }}>{w}{" "}</span>;
          })}
        </div>
        {p.author ? (
          <div style={{ color: p.accentColor, fontSize: s * 0.7, fontWeight: 700, marginTop: s * 0.6, opacity: authorIn,
            transform: `translateY(${(1 - authorIn) * s * 0.3}px)` }}>
            — {p.author}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const QuoteCardComposition: React.FC = () => (
  <Composition id="QuoteCard" component={QuoteCard} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ quote: "" }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
