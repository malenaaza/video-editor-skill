// A subscribe button that slides in, gets pressed and turns into "subscribed" with a tick, with a line under it. Text
// comes from `overlays.py subscribe`, so this file only draws: never edit it for one video. The idea comes from the
// free Subscribe Reminder template of github.com/reactvideoeditor/remotion-templates (MIT), rewritten for this
// skill's brand and size props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { SubscribeReminderComposition } from "./SubscribeReminder";
//   ... <SubscribeReminderComposition />
// Render: npx remotion render src/index.ts SubscribeReminder out/subscribe.mov --props=subscribe-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type SubscribeReminderProps = {
  text: string;
  sub?: string;
  doneText?: string;
  pressFrame?: number;
  fontSize?: number;
  accentColor?: string;
  font?: string;
  fontFile?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = { sub: "", doneText: "", pressFrame: 36, fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", seconds: 4, fps: 30, width: 1920, height: 1080 };

export const SubscribeReminder: React.FC<SubscribeReminderProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const enter = spring({ frame: frame - 2, fps, config: { damping: 14, stiffness: 130 } });
  const leave = interpolate(frame, [durationInFrames - 12, durationInFrames - 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pressed = p.doneText !== "" && frame >= p.pressFrame;
  const press = interpolate(frame, [p.pressFrame, p.pressFrame + 3, p.pressFrame + 8], [1, 0.9, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const label = pressed ? p.doneText : p.text;
  const left = p.width * (vertical ? 0.06 : 0.07);
  return (
    <AbsoluteFill style={{ fontFamily: p.font }}>
      <div style={{ position: "absolute", left, top: p.height * (vertical ? 0.7 : 0.76), display: "flex", flexDirection: "column",
        alignItems: "flex-start", gap: s * 0.25, transform: `translateX(${((1 - enter) * -1.2 + leave * -1.2) * (s * 8 + left)}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: s * 0.35, padding: `${s * 0.3}px ${s * 0.7}px`, borderRadius: s * 0.35,
          backgroundColor: pressed ? "rgba(20,16,40,0.92)" : p.accentColor, color: "#FFFFFF", fontSize: s * 0.85, fontWeight: 800,
          boxShadow: "0 12px 30px rgba(0,0,0,0.4)", transform: `scale(${press})`, border: pressed ? `${s / 14}px solid ${p.accentColor}` : `${s / 14}px solid transparent` }}>
          {pressed ? (
            <svg viewBox="0 0 24 24" width={s * 0.8} height={s * 0.8}>
              <path d="M4 12.5 L9.5 18 L20 6.5" fill="none" stroke={p.accentColor} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width={s * 0.8} height={s * 0.8}>
              <path d="M12 3 a6 6 0 0 0 -6 6 v4 l-2 3 h16 l-2 -3 v-4 a6 6 0 0 0 -6 -6 z M10 19 a2 2 0 0 0 4 0 z" fill="#FFFFFF" />
            </svg>
          )}
          <span>{label}</span>
        </div>
        {p.sub ? <div style={{ color: "#FFFFFF", fontSize: s * 0.55, fontWeight: 700, textShadow: "0 3px 10px rgba(0,0,0,0.6)", paddingLeft: s * 0.2 }}>{p.sub}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

export const SubscribeReminderComposition: React.FC = () => (
  <Composition id="SubscribeReminder" component={SubscribeReminder} durationInFrames={120} fps={30} width={1920} height={1080}
    defaultProps={{ text: "Suscríbete" }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
