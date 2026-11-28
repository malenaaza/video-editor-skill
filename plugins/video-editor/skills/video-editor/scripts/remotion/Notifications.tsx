// Message notifications stacking in a corner (top centre on vertical video), each sliding in as the speaker says it:
// a phone filling with messages, emails arriving, an automation reporting back. Up to four show at once; a fifth
// pushes the first out. Texts and times come from `overlays.py notify`, so this file only draws: never edit it for
// one video. The idea comes from the free Notification Pop template of
// github.com/reactvideoeditor/remotion-templates (MIT), rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { NotificationsComposition } from "./Notifications";
//   ... <NotificationsComposition />
// Render: npx remotion render src/index.ts Notifications out/notify.mov --props=notify-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type Toast = { app: string; text: string; frame: number };

export type NotificationsProps = {
  notifications: Toast[];
  fontSize?: number;
  accentColor?: string;
  font?: string;
  fontFile?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = { fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", seconds: 6, fps: 30, width: 1920, height: 1080 };
const MAX_SHOWN = 4;

export const Notifications: React.FC<NotificationsProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const leave = interpolate(frame, [durationInFrames - 10, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const arrived = p.notifications.map((n, i) => ({ n, i })).filter(({ n }) => frame >= n.frame);
  const shown = arrived.slice(-MAX_SHOWN);
  const cardW = Math.min(p.width * (vertical ? 0.88 : 0.34), s * 11);
  const slot = s * 1.9;
  return (
    <AbsoluteFill style={{ fontFamily: p.font, opacity: leave }}>
      <div style={{ position: "absolute", top: p.height * (vertical ? 0.08 : 0.07), left: vertical ? (p.width - cardW) / 2 : undefined,
        right: vertical ? undefined : p.width * 0.04, width: cardW }}>
        {shown.map(({ n, i }, k) => {
          const fromNewest = shown.length - 1 - k;                       // 0 = the newest, at the top
          const pop = spring({ frame: frame - n.frame, fps, config: { damping: 14, stiffness: 150 } });
          const pushedOut = arrived.length - MAX_SHOWN > 0 && k === 0 ? 1 : 0;
          return (
            <div key={i} style={{ position: "absolute", top: fromNewest * slot, width: cardW, display: "flex", alignItems: "center",
              gap: s * 0.4, boxSizing: "border-box", padding: `${s * 0.25}px ${s * 0.4}px`, borderRadius: s * 0.4, backgroundColor: "rgba(255,255,255,0.95)",
              boxShadow: "0 12px 30px rgba(0,0,0,0.3)", transform: `translateX(${(1 - pop) * cardW * (vertical ? 0 : 1.1)}px) translateY(${(1 - pop) * (vertical ? -s : 0)}px)`,
              opacity: Math.min(1, pop * 1.5) * (1 - 0.18 * fromNewest) * (1 - pushedOut * 0.4) }}>
              <div style={{ width: s * 1.1, height: s * 1.1, borderRadius: s * 0.3, backgroundColor: p.accentColor, color: "#FFFFFF", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: s * 0.65, fontWeight: 900 }}>
                {(n.app || "•").trim().charAt(0).toUpperCase()}
              </div>
              <div style={{ minWidth: 0 }}>
                {n.app ? <div style={{ color: "#6B6B78", fontSize: s * 0.38, fontWeight: 700, textTransform: "uppercase", letterSpacing: s * 0.02 }}>{n.app}</div> : null}
                <div style={{ color: "#1F1F29", fontSize: s * 0.5, fontWeight: 700, lineHeight: 1.15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.text}</div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const NotificationsComposition: React.FC = () => (
  <Composition id="Notifications" component={Notifications} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ notifications: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
