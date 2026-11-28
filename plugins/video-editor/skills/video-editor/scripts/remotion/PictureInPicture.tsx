// A picture or a short video in a framed window in a corner while the speaker keeps talking: a tool's screen, a
// photo, a result. A video is muted, so the speaker stays the only voice. The file is in the project's public
// folder. Settings come from `overlays.py pip`, so this file only draws: never edit it for one video. The idea
// comes from the free Picture in Picture template of github.com/reactvideoeditor/remotion-templates (MIT),
// rewritten for this skill's brand and timing props.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { PictureInPictureComposition } from "./PictureInPicture";
//   ... <PictureInPictureComposition />
// Render: npx remotion render src/index.ts PictureInPicture out/pip.mov --props=pip-props.json
import React from "react";
import { AbsoluteFill, Composition, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type PictureInPictureProps = {
  src: string;
  kind: "image" | "video";
  corner?: "top-left" | "top-right" | "bottom-left" | "bottom-right";
  size?: number; // its width as a share of the video's
  ratio?: number; // width / height of the window
  label?: string;
  videoStart?: number; // seconds into the video the window starts at
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
  corner: "top-right" as const, size: 0.32, ratio: 16 / 9, label: "", videoStart: 0, fontSize: 54, accentColor: "#FF4F8B",
  font: "sans-serif", fontFile: "", seconds: 5, fps: 30, width: 1920, height: 1080,
};

export const PictureInPicture: React.FC<PictureInPictureProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const enter = spring({ frame: frame - 2, fps, config: { damping: 15, stiffness: 140 } });
  const leave = interpolate(frame, [durationInFrames - 10, durationInFrames - 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const w = p.width * p.size;
  const h = w / p.ratio;
  const margin = p.width * 0.035;
  const right = p.corner.endsWith("right");
  const top = p.corner.startsWith("top");
  const shown = Math.max(0, Math.min(1, enter - leave));
  const style: React.CSSProperties = {
    position: "absolute", width: w, height: h, [right ? "right" : "left"]: margin, [top ? "top" : "bottom"]: margin * (top ? 1 : 2.6),
    borderRadius: s * 0.3, overflow: "hidden", border: `${s / 12}px solid ${p.accentColor}`, boxShadow: "0 16px 40px rgba(0,0,0,0.45)",
    backgroundColor: "#000", opacity: Math.min(1, shown * 1.4), transform: `scale(${0.8 + 0.2 * shown})`,
  };
  const media: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover" };
  return (
    <AbsoluteFill style={{ fontFamily: p.font }}>
      <div style={style}>
        {p.kind === "video" ? (
          <OffthreadVideo src={staticFile(p.src)} muted startFrom={Math.round(p.videoStart * fps)} style={media} />
        ) : (
          <Img src={staticFile(p.src)} style={media} />
        )}
        {p.label ? (
          <div style={{ position: "absolute", left: 0, bottom: 0, padding: `${s * 0.12}px ${s * 0.4}px`, backgroundColor: p.accentColor, color: "#FFFFFF",
            fontSize: s * 0.45, fontWeight: 800, borderTopRightRadius: s * 0.25 }}>{p.label}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const PictureInPictureComposition: React.FC = () => (
  <Composition id="PictureInPicture" component={PictureInPicture} durationInFrames={150} fps={30} width={1920} height={1080}
    defaultProps={{ src: "", kind: "image" as const }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
