// Three to six steps of a process in a row (a column on vertical video). Each step lights up as the speaker says
// it, the one before it turns into a tick, and a line fills between them. Times come from `overlays.py steps`, so
// this file only draws: never edit it for one video. The idea comes from the free Progress Steps template of
// github.com/reactvideoeditor/remotion-templates (MIT), rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ProgressStepsComposition } from "./ProgressSteps";
//   ... <ProgressStepsComposition />
// Render: npx remotion render src/index.ts ProgressSteps out/steps.mov --props=steps-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type Step = { label: string; frame: number };

export type ProgressStepsProps = {
  steps: Step[];
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
  background2: "#0E2A47", seconds: 8, fps: 30, width: 1920, height: 1080,
};

export const ProgressSteps: React.FC<ProgressStepsProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const over = p.background === "transparent";
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const n = p.steps.length;
  const badge = s * 1.5;
  const slot = vertical ? s * 1.9 : Math.min((p.width * 0.86) / n, s * 7);
  const titlePop = spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  const next = (i: number) => (i + 1 < n ? p.steps[i + 1].frame : Infinity);
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      {p.title ? (
        <div style={{ color: "#FFFFFF", fontSize: s * 1.5, fontWeight: 900, textAlign: "center", textTransform: "uppercase",
          marginBottom: s * 1.1, textShadow: over ? "0 4px 16px rgba(0,0,0,0.5)" : "none",
          transform: `scale(${0.6 + 0.4 * titlePop})`, opacity: Math.min(1, titlePop * 1.5) }}>
          {p.title}
        </div>
      ) : null}
      <div style={{ display: "flex", flexDirection: vertical ? "column" : "row", alignItems: vertical ? "flex-start" : "flex-start" }}>
        {p.steps.map((st, i) => {
          const reached = frame >= st.frame;
          const done = frame >= next(i);
          const pop = reached ? spring({ frame: frame - st.frame, fps, config: { damping: 10, stiffness: 170 } }) : 0;
          const tick = done ? interpolate(frame, [next(i), next(i) + 8], [0, 1], { extrapolateRight: "clamp" }) : 0;
          const line = i + 1 < n
            ? interpolate(frame, [p.steps[i + 1].frame - Math.round(fps * 0.35), p.steps[i + 1].frame], [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
            : 0;
          const lineLen = slot - badge;
          return (
            <div key={i} style={{ display: "flex", flexDirection: vertical ? "row" : "column", alignItems: "flex-start",
              width: vertical ? undefined : i + 1 < n ? slot : badge }}>
              <div style={{ display: "flex", flexDirection: vertical ? "column" : "row", alignItems: "center" }}>
                <div style={{ width: badge, height: badge, borderRadius: "50%", position: "relative", flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: s * 0.8, fontWeight: 800,
                  border: `${s / 12}px solid ${reached ? p.accentColor : "rgba(255,255,255,0.45)"}`,
                  backgroundColor: reached ? p.accentColor : "rgba(255,255,255,0.12)",
                  color: reached ? "#FFFFFF" : "rgba(255,255,255,0.8)",
                  transform: `scale(${reached ? 0.8 + 0.4 * pop - (done ? 0.2 : 0) : 1})`,
                  boxShadow: reached && !done ? `0 0 ${s * 0.6}px ${p.accentColor}` : "none" }}>
                  <span style={{ opacity: 1 - tick }}>{i + 1}</span>
                  <svg viewBox="0 0 24 24" width={badge * 0.55} height={badge * 0.55} style={{ position: "absolute", opacity: tick }}>
                    <path d="M4 12.5 L9.5 18 L20 6.5" fill="none" stroke="#FFFFFF" strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                {i + 1 < n ? (
                  <div style={{ position: "relative", backgroundColor: "rgba(255,255,255,0.25)", borderRadius: s,
                    width: vertical ? s / 10 : lineLen, height: vertical ? lineLen : s / 10 }}>
                    <div style={{ position: "absolute", left: 0, top: 0, backgroundColor: p.accentColor, borderRadius: s,
                      width: vertical ? "100%" : `${line * 100}%`, height: vertical ? `${line * 100}%` : "100%" }} />
                  </div>
                ) : null}
              </div>
              <div style={vertical
                ? { height: badge, display: "flex", alignItems: "center", marginLeft: s * 0.4 }
                : { position: "relative", width: badge, marginTop: s * 0.3 }}>
                <div style={{ color: "#FFFFFF", fontWeight: 700, fontSize: s * 0.62, whiteSpace: "nowrap",
                  ...(vertical ? {} : { position: "absolute", left: "50%", transform: "translateX(-50%)" }),
                  opacity: reached ? Math.min(1, pop * 1.5) : 0.35 }}>
                  {st.label}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const ProgressStepsComposition: React.FC = () => (
  <Composition id="ProgressSteps" component={ProgressSteps} durationInFrames={240} fps={30} width={1920} height={1080}
    defaultProps={{ steps: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
