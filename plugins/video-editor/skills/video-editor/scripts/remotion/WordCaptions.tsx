// Word highlight captions: the brand's captions, with a rounded box in the accent colour that wipes in behind
// each word while it is said and fades when the word ends. Every word of a caption is in place from the start,
// so the line never moves; a soft shadow keeps the other words readable on any background.
// Renders one transparent clip the length of the video; place it with FFmpeg instead of burning captions.ass
// (see references/graphics.md).
//
// The props come from captions.py, so captions, timing, size, position and line breaks match the normal captions:
//   python -I <skill>/scripts/captions.py ... --remotion-props word-captions.json --accent-color "#FF4F8B" --fps 30
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { WordCaptionsComposition } from "./WordCaptions";
//   ... <WordCaptionsComposition />
// Render:
//   npx remotion render src/index.ts WordCaptions out/captions.mov --codec=prores --prores-profile=4444
//     --pixel-format=yuva444p10le --image-format=png --props=word-captions.json
// Add "fontFile": "fonts/<file>.ttf" (inside public/) to the props to load the brand font from a file.
import React from "react";
import { AbsoluteFill, Composition, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type WordCaption = {
  start: number; // seconds in the finished video
  end: number;
  words: [number, number, string][]; // [start, end, text as shown]
  breakAfter?: number; // words on the first line when the caption has two lines (0: one line)
};

export type WordCaptionsProps = {
  captions: WordCaption[];
  length?: number; // seconds; the clip lasts this long (default: the last caption's end)
  font?: string;
  fontFile?: string;
  fontSize?: number;
  textColor?: string;
  accentColor?: string; // the box behind the word being said
  bottom?: number; // pixels from the bottom of the frame to the bottom of the caption (captions.py --margin-v)
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  font: "sans-serif",
  fontSize: 64,
  textColor: "#FFFFFF",
  accentColor: "#FF4F8B",
  bottom: 520,
  fps: 30,
  width: 1080,
  height: 1920,
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const Word: React.FC<{ word: [number, number, string]; t: number; p: typeof defaults }> = ({ word, t, p }) => {
  const [start, end, text] = word;
  const wipeIn = Math.max(0.04, Math.min(0.15, end - start)); // short words wipe faster, so the box is full while said
  const shown = interpolate(t, [start, start + wipeIn], [0, 1], clamp);
  const fade = interpolate(t, [end, end + 0.1], [1, 0], clamp);
  const lit = shown > 0 && fade > 0;
  return (
    <span style={{ position: "relative", display: "inline-block", padding: `${p.fontSize * 0.1}px ${p.fontSize * 0.2}px ${p.fontSize * 0.14}px`,
      isolation: "isolate" }}>
      {lit ? (
        <span style={{ position: "absolute", inset: 0, zIndex: -1, background: p.accentColor, borderRadius: p.fontSize * 0.2,
          transform: `scaleX(${shown})`, transformOrigin: "left center", opacity: fade,
          boxShadow: `0 ${p.fontSize * 0.15}px ${p.fontSize * 0.35}px rgba(0,0,0,0.25)` }} />
      ) : null}
      {text}
    </span>
  );
};

export const WordCaptions: React.FC<WordCaptionsProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const cap = p.captions.find((c) => c.start <= t && t < c.end);
  if (!cap) return null;
  const opacity = interpolate(t, [cap.start, cap.start + 0.1, cap.end - 0.08, cap.end], [0, 1, 1, 0], clamp);
  const split = cap.breakAfter && cap.breakAfter < cap.words.length ? cap.breakAfter : cap.words.length;
  const lines = [cap.words.slice(0, split), cap.words.slice(split)].filter((l) => l.length > 0);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: p.bottom, opacity }}>
      {lines.map((line, li) => (
        <div key={li} style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: p.fontSize * 0.06,
          maxWidth: p.width - 120, fontFamily: p.font, fontSize: p.fontSize, fontWeight: 800, lineHeight: 1.05,
          color: p.textColor, textShadow: `0 ${p.fontSize * 0.07}px ${p.fontSize * 0.22}px rgba(0,0,0,0.5)` }}>
          {line.map((w, wi) => <Word key={wi} word={w} t={t} p={p} />)}
        </div>
      ))}
    </AbsoluteFill>
  );
};

export const WordCaptionsComposition: React.FC = () => (
  <Composition
    id="WordCaptions"
    component={WordCaptions}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
    // Only the required prop, empty: Remotion merges these into every render, so sample captions would leak.
    defaultProps={{ captions: [] } as WordCaptionsProps}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      const last = p.captions.length ? p.captions[p.captions.length - 1].end : 3;
      return { durationInFrames: Math.max(1, Math.round((p.length ?? last) * p.fps)), fps: p.fps, width: p.width, height: p.height };
    }}
  />
);
