// Two to five bars to compare, each growing as the speaker says its value, with the number counting up on it, written
// the Spanish way. Values and times come from `overlays.py barchart`, so this file only draws: never edit it for one
// video. The idea comes from the free Bar Chart template of github.com/reactvideoeditor/remotion-templates (MIT),
// rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { BarChartComposition } from "./BarChart";
//   ... <BarChartComposition />
// Render: npx remotion render src/index.ts BarChart out/bars.mov --props=barchart-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type Bar = { label: string; value: number; frame: number };

export type BarChartProps = {
  bars: Bar[];
  max?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
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
  max: 0, decimals: 0, prefix: "", suffix: "", title: "", fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif",
  fontFile: "", background: "#1B1033", background2: "#0E2A47", seconds: 6, fps: 30, width: 1920, height: 1080,
};

const formatEs = (value: number, decimals: number) => {
  const [whole, part] = value.toFixed(decimals).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return part ? `${grouped},${part}` : grouped;
};

export const BarChart: React.FC<BarChartProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const over = p.background === "transparent";
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const maximum = p.max > 0 ? p.max : Math.max(1, ...p.bars.map((b) => b.value));
  const panelW = p.width * (vertical ? 0.88 : 0.62);
  const labelW = s * (vertical ? 3.4 : 4.2);
  const trackW = panelW - labelW - s * 0.6;
  const titlePop = spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div style={{ width: panelW, ...(over ? { backgroundColor: "rgba(20,16,40,0.85)", borderRadius: s * 0.5, padding: `${s * 0.6}px ${s * 0.6}px` } : {}) }}>
        {p.title ? (
          <div style={{ color: "#FFFFFF", fontSize: s * 1.2, fontWeight: 900, textAlign: "center", marginBottom: s * 0.7,
            textTransform: "uppercase", transform: `scale(${0.6 + 0.4 * titlePop})`, opacity: Math.min(1, titlePop * 1.5) }}>
            {p.title}
          </div>
        ) : null}
        {p.bars.map((b, i) => {
          const grow = interpolate(frame, [b.frame, b.frame + Math.round(fps * 0.9)], [0, 1],
            { easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const seen = frame >= b.frame;
          const length = Math.max(s * 0.5, trackW * (b.value / maximum) * grow);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", marginBottom: s * 0.45, opacity: seen ? 1 : 0.35 }}>
              <div style={{ width: labelW, color: "#FFFFFF", fontSize: s * 0.65, fontWeight: 700, paddingRight: s * 0.3 }}>{b.label}</div>
              <div style={{ width: trackW, height: s * 0.95, borderRadius: s * 0.3, backgroundColor: "rgba(255,255,255,0.12)" }}>
                {seen ? (
                  <div style={{ width: length, height: "100%", borderRadius: s * 0.3, backgroundColor: p.accentColor, display: "flex",
                    alignItems: "center", justifyContent: "flex-end", paddingRight: s * 0.25, boxSizing: "border-box" }}>
                    <span style={{ color: "#FFFFFF", fontSize: s * 0.6, fontWeight: 800, whiteSpace: "nowrap" }}>
                      {p.prefix}{formatEs(b.value * grow, p.decimals)}{p.suffix}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const BarChartComposition: React.FC = () => (
  <Composition id="BarChart" component={BarChart} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ bars: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
