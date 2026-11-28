// Big numbers counting down (3, 2, 1), each slamming in with a ring that empties around it, then an optional word
// ("¡YA!"). Numbers and times come from `overlays.py countdown`, so this file only draws: never edit it for one
// video. The idea comes from the free Countdown Timer template of github.com/reactvideoeditor/remotion-templates
// (MIT), rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { CountdownComposition } from "./Countdown";
//   ... <CountdownComposition />
// Render: npx remotion render src/index.ts Countdown out/countdown.mov --props=countdown-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type CountStep = { text: string; frame: number };

export type CountdownProps = {
  numbers: CountStep[];
  everyFrames?: number;
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
  everyFrames: 30, fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", background: "#1B1033",
  background2: "#0E2A47", seconds: 5, fps: 30, width: 1920, height: 1080,
};

export const Countdown: React.FC<CountdownProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const over = p.background === "transparent";
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  let index = -1;
  p.numbers.forEach((n, i) => { if (frame >= n.frame) index = i; });
  const current = index >= 0 ? p.numbers[index] : null;
  const isWord = current !== null && !/^\d+$/.test(current.text);
  const local = current ? frame - current.frame : 0;
  const pop = current ? spring({ frame: local, fps, config: { damping: 9, stiffness: 200 } }) : 0;
  const size = s * 5;
  const r = size / 2 - s / 6;
  const circ = 2 * Math.PI * r;
  const empty = interpolate(local, [0, p.everyFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const out = isWord ? 1 : interpolate(local, [p.everyFrames - 6, p.everyFrames], [1, 0.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center", opacity: leave,
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      {current ? (
        <div style={{ position: "relative", width: isWord ? undefined : size, height: size, display: "flex", alignItems: "center",
          justifyContent: "center", transform: `scale(${0.4 + 0.6 * pop})`, opacity: Math.min(1, pop * 1.5) * (isWord ? 1 : Math.max(0.25, out)) }}>
          {!isWord ? (
            <svg width={size} height={size} style={{ position: "absolute", transform: "rotate(-90deg)" }}>
              <circle cx={size / 2} cy={size / 2} r={r} fill={over ? "rgba(20,16,40,0.8)" : "none"} stroke="rgba(255,255,255,0.2)" strokeWidth={s / 6} />
              <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={p.accentColor} strokeWidth={s / 6} strokeLinecap="round"
                strokeDasharray={circ} strokeDashoffset={circ * empty} />
            </svg>
          ) : null}
          <div style={{ color: isWord ? p.accentColor : "#FFFFFF", fontSize: isWord ? s * 3 : s * 3.4, fontWeight: 900, lineHeight: 1,
            textShadow: over ? "0 6px 24px rgba(0,0,0,0.55)" : "none", textTransform: "uppercase" }}>
            {current.text}
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const CountdownComposition: React.FC = () => (
  <Composition id="Countdown" component={Countdown} durationInFrames={150} fps={30} width={1920} height={1080}
    defaultProps={{ numbers: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
