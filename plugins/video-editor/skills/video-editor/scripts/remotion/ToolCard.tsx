// Tool cards for videos about AI: a white pill with the tool's logo (or a badge with its initial) and its name slides
// in from the side a beat before the speaker names it; tools named one after another stack, each on its own word;
// the group slides out at the end. Times and positions come from scripts/toolcards.py, so this file only draws:
// never edit it for one video. Logos only from each brand's own press kit, copied into public/.
// Renders as a short transparent clip (ProRes 4444) placed over the video with FFmpeg.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ToolCardComposition } from "./ToolCard";
//   ... <ToolCardComposition />
// Render one group:
//   npx remotion render src/index.ts ToolCard out/card-1.mov --props=toolcards/card-1.json --codec=prores
//     --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
import React from "react";
import { AbsoluteFill, Composition, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ToolCardItem = { name: string; logo?: string; frame: number };

export type ToolCardProps = {
  cards: ToolCardItem[];
  side?: "left" | "right";
  top?: number;
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
  side: "left" as "left" | "right",
  top: 1050,
  fontSize: 64,
  accentColor: "#FF4F8B",
  font: "sans-serif",
  fontFile: "",
  seconds: 3,
  fps: 30,
  width: 1080,
  height: 1920,
};

export const ToolCard: React.FC<ToolCardProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const margin = Math.round(p.width * 0.05);
  const out = interpolate(frame, [durationInFrames - Math.round(fps * 0.35), durationInFrames - 1], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const away = p.side === "left" ? -1 : 1;
  return (
    <AbsoluteFill style={{ fontFamily: p.font }}>
      <div style={{ position: "absolute", top: p.top, [p.side]: margin, display: "flex", flexDirection: "column",
        alignItems: p.side === "left" ? "flex-start" : "flex-end", gap: s * 0.35 }}>
        {p.cards.map((c, i) => {
          if (frame < c.frame) return null;
          const enter = spring({ frame: frame - c.frame, fps, config: { damping: 20, stiffness: 170 } });
          const shift = (1 - enter + out) * away * (s * 6);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: s * 0.4, backgroundColor: "#FFFFFF",
              color: "#1A1A1A", borderRadius: s, padding: `${s * 0.22}px ${s * 0.6}px ${s * 0.22}px ${s * 0.22}px`,
              boxShadow: "0 10px 30px rgba(0,0,0,0.30)", fontSize: s * 0.62, fontWeight: 800,
              transform: `translateX(${shift}px)`, opacity: Math.min(1, enter * 1.6) * (1 - out) }}>
              {c.logo ? (
                <Img src={staticFile(c.logo)} style={{ width: s, height: s, objectFit: "contain" }} />
              ) : (
                <div style={{ width: s, height: s, borderRadius: s / 2, backgroundColor: p.accentColor, color: "#FFFFFF",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: s * 0.5 }}>
                  {c.name.slice(0, 1).toUpperCase()}
                </div>
              )}
              {c.name}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const ToolCardComposition: React.FC = () => (
  <Composition
    id="ToolCard"
    component={ToolCard}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ cards: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
