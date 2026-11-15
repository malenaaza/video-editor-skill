// Animated hook title for the first seconds of a video: each line's box wipes in,
// the words rise in one after another, and everything slides up and out at the end.
// Renders as a short transparent clip; place it on the video with FFmpeg (see SKILL.md).
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it
// in src/Root.tsx:
//   import { TitleCardComposition } from "./TitleCard";
//   ... <TitleCardComposition />
// Render one:
//   npx remotion render src/index.ts TitleCard out/title.mov --codec=prores --prores-profile=4444
//     --pixel-format=yuva444p10le --image-format=png --props=title-props.json
// Put the props in a JSON file (title-props.json) rather than on the command line, so quotes
// and emoji in the text survive on Windows. Every prop is optional except lines. Match fps,
// width and height to the video the title goes into.
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type TitleCardProps = {
  lines: string[]; // 1 to 3 short lines, e.g. ["3 serums", "I'd buy again"]
  highlight?: string; // a word drawn in the accent color, e.g. "again"
  font?: string;
  fontFile?: string; // inside public/, e.g. "fonts/Montserrat-Bold.ttf"
  fontSize?: number;
  textColor?: string;
  boxColor?: string; // "transparent" for text with no box
  accentColor?: string;
  top?: number; // y of the first line; keep it below the app's top bar and off the face
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  font: "sans-serif",
  fontSize: 96,
  textColor: "#FFFFFF",
  boxColor: "#111111",
  accentColor: "#FF4F8B",
  top: 260,
  seconds: 2.5,
  fps: 30,
  width: 1080,
  height: 1920,
};

const clean = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

export const TitleCard: React.FC<TitleCardProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  let wordIndex = 0;

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        paddingTop: p.top,
        gap: p.fontSize * 0.12,
        opacity: 1 - exit,
        transform: `translateY(${-exit * 40}px)`,
      }}
    >
      {p.lines.map((line, li) => {
        const wipe = spring({ frame: frame - li * 4, fps, config: { damping: 200 }, durationInFrames: 10 });
        return (
          <div
            key={li}
            style={{
              position: "relative",
              padding: `${p.fontSize * 0.08}px ${p.fontSize * 0.3}px`,
              maxWidth: p.width - 120,
              textAlign: "center",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: p.boxColor,
                borderRadius: p.fontSize * 0.18,
                transform: `scaleX(${wipe})`,
                transformOrigin: "left center",
              }}
            />
            {line.split(" ").map((word, wi, words) => {
              const rise = spring({ frame: frame - 3 - wordIndex++ * 3, fps, config: { damping: 12, mass: 0.6 } });
              const isHighlight = p.highlight !== undefined && clean(word) === clean(p.highlight);
              return (
                <span
                  key={wi}
                  style={{
                    position: "relative",
                    display: "inline-block",
                    marginRight: wi < words.length - 1 ? p.fontSize * 0.25 : 0,
                    fontFamily: p.font,
                    fontSize: p.fontSize,
                    fontWeight: 800,
                    lineHeight: 1.1,
                    color: isHighlight ? p.accentColor : p.textColor,
                    opacity: rise,
                    transform: `translateY(${(1 - rise) * p.fontSize * 0.5}px)`,
                  }}
                >
                  {word}
                </span>
              );
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const TitleCardComposition: React.FC = () => (
  <Composition
    id="TitleCard"
    component={TitleCard}
    durationInFrames={75}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ lines: ["3 serums", "I'd buy again"], highlight: "again" } as TitleCardProps}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { durationInFrames: Math.round(p.seconds * p.fps), fps: p.fps, width: p.width, height: p.height };
    }}
  />
);
