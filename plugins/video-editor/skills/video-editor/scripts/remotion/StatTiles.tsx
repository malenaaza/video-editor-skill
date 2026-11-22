// Two to four numbers that belong together, each tile popping in and counting up as the speaker says it, written
// the Spanish way (1.250,5). Times come from `overlays.py stats`, so this file only draws: never edit it for one video.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { StatTilesComposition } from "./StatTiles";
//   ... <StatTilesComposition />
// Render: npx remotion render src/index.ts StatTiles out/stats.mov --props=stats-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type StatTile = { value: number; decimals: number; prefix: string; suffix: string; label: string; frame: number };

export type StatTilesProps = {
  tiles: StatTile[];
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

const formatEs = (value: number, decimals: number) => {
  const [whole, part] = value.toFixed(decimals).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return part ? `${grouped},${part}` : grouped;
};

export const StatTiles: React.FC<StatTilesProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const over = p.background === "transparent";
  const columns = vertical ? (p.tiles.length > 2 ? 2 : 1) : p.tiles.length;
  const tileW = vertical ? p.width * (columns === 1 ? 0.8 : 0.42) : Math.min(p.width * 0.8 / p.tiles.length, s * 9);
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      {p.title ? (
        <div style={{ position: "absolute", top: p.height * (vertical ? 0.16 : 0.12), width: "100%", textAlign: "center",
          color: "#FFFFFF", fontSize: s * 1.05, fontWeight: 800,
          opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" }) }}>
          {p.title}
        </div>
      ) : null}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${columns}, ${tileW}px)`, gap: s * 0.6 }}>
        {p.tiles.map((t, i) => {
          if (frame < t.frame) return <div key={i} />;
          const pop = spring({ frame: frame - t.frame, fps, config: { damping: 16, stiffness: 160 } });
          const counted = interpolate(frame, [t.frame, t.frame + Math.round(fps * 0.8)], [0, t.value],
            { easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ backgroundColor: "#FFFFFF", borderRadius: s * 0.5, padding: `${s * 0.6}px ${s * 0.5}px`,
              textAlign: "center", boxShadow: "0 20px 50px rgba(0,0,0,0.30)", borderTop: `${s / 8}px solid ${p.accentColor}`,
              transform: `translateY(${(1 - pop) * s}px)`, opacity: pop }}>
              <div style={{ fontSize: s * 2.2, fontWeight: 800, color: p.accentColor, whiteSpace: "nowrap" }}>
                {t.prefix}{formatEs(counted, t.decimals)}{t.suffix}
              </div>
              <div style={{ fontSize: s * 0.7, fontWeight: 600, color: "#2A2A33", marginTop: s * 0.15 }}>{t.label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const StatTilesComposition: React.FC = () => (
  <Composition id="StatTiles" component={StatTiles} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ tiles: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
