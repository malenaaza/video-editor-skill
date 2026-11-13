// One short transparent clip per emoji: a spring pop, a small wobble and a soft shadow.
// Render each emoji on its own and place it on the timeline with FFmpeg (see SKILL.md),
// which is much faster than one transparent overlay as long as the whole video.
//
// Register it in src/Root.tsx:
//   import { EmojiPopComposition } from "./EmojiPop";
//   ... <EmojiPopComposition />
// Render one:
//   npx remotion render src/index.ts EmojiPop out/emoji-01.mov --codec=prores --prores-profile=4444
//     --pixel-format=yuva444p10le --image-format=png --props='{"emoji":"💸","left":790,"top":1120}'
// Set fps, width and height below to match the video the emoji goes into.
//
// Emoji font: Noto Color Emoji is free to reuse (SIL Open Font License). Install it, or keep
// the fallback to the system emoji font. Don't use Apple's emoji: they can't be reused freely.
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type EmojiProps = { emoji: string; left: number; top: number };

export const EmojiPop: React.FC<EmojiProps> = ({ emoji, left, top }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 8, mass: 0.5 } });
  const leave = interpolate(frame, [durationInFrames - 4, durationInFrames - 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const wobble = Math.sin(frame / 3.2) * 5;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left,
          top,
          width: 190,
          textAlign: "center",
          fontSize: 150,
          lineHeight: 1,
          fontFamily: '"Noto Color Emoji", "Segoe UI Emoji", sans-serif',
          filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.3))",
          transform: `scale(${pop * leave}) rotate(${wobble - 6}deg)`,
        }}
      >
        {emoji}
      </div>
    </AbsoluteFill>
  );
};

export const EmojiPopComposition: React.FC = () => (
  <Composition
    id="EmojiPop"
    component={EmojiPop}
    durationInFrames={43}
    fps={24}
    width={1080}
    height={1920}
    defaultProps={{ emoji: "✨", left: 790, top: 1120 }}
  />
);
