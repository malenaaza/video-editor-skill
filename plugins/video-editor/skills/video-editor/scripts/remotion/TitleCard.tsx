// Animated hook title for the first seconds of a video. Two animations:
//   "pop" (default): each line's box wipes in, the words rise in one after another;
//   "typewriter": the box wipes in, then the letters are typed one by one with a blinking cursor in the accent
//                 colour, and the title gives a small bounce when it's complete. The layout never moves while typing:
//                 letters not typed yet are already in place, invisible. For key clicks, scripts/sfx/typing.py makes
//                 the matching sound from the same text and speed.
// Both slide up and out at the end.
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
  animation?: "pop" | "typewriter";
  lettersPerSecond?: number; // typewriter speed (default 16: a 20-letter title types in about 1.3 s)
  typingStart?: number; // seconds before the first letter (default 0.13, while the box wipes in)
  cursor?: boolean; // typewriter cursor (default true)
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
  animation: "pop" as "pop" | "typewriter",
  lettersPerSecond: 16,
  typingStart: 0.13,
  cursor: true,
  seconds: 2.5,
  fps: 30,
  width: 1080,
  height: 1920,
};

const clean = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

// Typewriter timing, shared with calculateMetadata: every character (spaces too) takes 1 / lettersPerSecond.
const typedLength = (lines: string[]) => lines.reduce((n, line) => n + Array.from(line).length, 0);
const typingSeconds = (p: { lines: string[]; lettersPerSecond: number; typingStart: number }) =>
  p.typingStart + typedLength(p.lines) / p.lettersPerSecond;

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
  const typewriter = p.animation === "typewriter";
  const typed = typewriter ? Math.floor(Math.max(0, frame / fps - p.typingStart) * p.lettersPerSecond) : 0;
  const total = typedLength(p.lines);
  const doneAt = Math.round(typingSeconds(p) * fps);
  const bounce = typewriter
    ? interpolate(frame, [doneAt, doneAt + 4, doneAt + 9], [1, 1.06, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;
  const blinkOn = typed < total || Math.floor(frame / (fps * 0.27)) % 2 === 0; // steady while typing, blinks after
  let charIndex = 0;

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        paddingTop: p.top,
        gap: p.fontSize * 0.12,
        opacity: 1 - exit,
        transform: `translateY(${-exit * 40}px) scale(${bounce})`,
      }}
    >
      {p.lines.map((line, li) => {
        // typewriter: each line's box wipes in just before its first letter, so no empty box waits on screen
        const lineStart = typedLength(p.lines.slice(0, li));
        const boxAt = typewriter ? Math.max(0, Math.round((p.typingStart + lineStart / p.lettersPerSecond) * fps) - 3) : li * 4;
        const wipe = spring({ frame: frame - boxAt, fps, config: { damping: 200 }, durationInFrames: 10 });
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
              if (typewriter) {
                const chars = Array.from(word + (wi < words.length - 1 ? " " : ""));
                return (
                  <span key={wi} style={{ position: "relative", fontFamily: p.font, fontSize: p.fontSize, fontWeight: 800, lineHeight: 1.1,
                    color: isHighlight ? p.accentColor : p.textColor, whiteSpace: "pre" }}>
                    {chars.map((ch, ci) => {
                      const index = charIndex++;
                      const showCursor = p.cursor && blinkOn && index === Math.min(typed, total) - 1;
                      return (
                        <span key={ci} style={{ opacity: index < typed ? 1 : 0 }}>
                          {ch}
                          {showCursor ? (
                            <span style={{ display: "inline-block", width: p.fontSize * 0.08, height: p.fontSize * 0.95,
                              marginLeft: p.fontSize * 0.04, background: p.accentColor, verticalAlign: "-0.12em", opacity: 1 }} />
                          ) : null}
                        </span>
                      );
                    })}
                  </span>
                );
              }
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
    // Only the required lines here: Remotion merges these into every render, so a sample highlight would leak.
    defaultProps={{ lines: ["Your title"] } as TitleCardProps}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      // a typewriter title lasts long enough to finish typing and still be read for about a second
      const seconds = p.animation === "typewriter" ? Math.max(p.seconds, typingSeconds(p) + 1.1) : p.seconds;
      return { durationInFrames: Math.round(seconds * p.fps), fps: p.fps, width: p.width, height: p.height };
    }}
  />
);
