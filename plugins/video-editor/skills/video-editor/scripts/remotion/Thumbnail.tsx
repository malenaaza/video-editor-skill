// YouTube thumbnail (1280x720): the speaker's face big on one side, two to four huge words on the other, in the
// brand's colours. Faces and short, high-contrast text are what people read at phone size, where a thumbnail is
// about 170 px wide; anything small is lost. Optional: a picture on the text side (a screenshot, a tool's logo).
// Renders a single PNG with `npx remotion still` (see references/cover.md, YouTube thumbnail).
//
// The face: give faceX, faceY, faceSize, bgWidth and bgHeight from scripts/cover/face_box.py on the frame. The frame
// is enlarged so the face is about 45% of the height and moved so it sits on its side, always covering the picture.
// Pick a frame with an expression (eyes open, mid-reaction), not mid-word with the mouth half open.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ThumbnailComposition } from "./Thumbnail";
//   ... <ThumbnailComposition />
// Render:
//   npx remotion still src/index.ts Thumbnail out/thumbnail.png --props=thumbnail.json
// Image paths are inside the project's public folder: copy the frame (and the picture, if any) there first.
import React from "react";
import { AbsoluteFill, Img, Still, staticFile } from "remotion";
import { useBrandFont } from "./brandFont";

export type ThumbnailProps = {
  background: string; // frame of the speaker, inside public/, e.g. "thumb/frame.png"
  bgWidth: number; // the frame's size in pixels (face_box.py prints it)
  bgHeight: number;
  faceX: number; // middle of the face, in pixels of the frame (face_box.py)
  faceY: number;
  faceSize: number; // forehead-to-chin height in pixels
  lines: string[]; // 1 to 3 short lines, 2 to 4 words in all, e.g. ["5 PROMPTS", "QUE USO"]
  highlight?: string; // one word in the accent colour, e.g. "PROMPTS"
  side?: "left" | "right"; // where the face goes (the words take the other side)
  picture?: string; // optional, inside public/: a screenshot or logo shown on the words' side
  faceShare?: number; // face height as a share of the thumbnail's height (0.45)
  font?: string;
  fontFile?: string;
  fontSize?: number; // the biggest line; longer lines shrink to fit
  textColor?: string;
  accentColor?: string;
  panelColor?: string; // the colour behind the words, fading into the picture
  width?: number;
  height?: number;
};

const defaults = {
  side: "right" as "left" | "right",
  faceShare: 0.45,
  font: "sans-serif",
  fontSize: 150,
  textColor: "#FFFFFF",
  accentColor: "#FF4F8B",
  panelColor: "#111111",
  width: 1280,
  height: 720,
};

const SAFE = 40; // keep words this far from every edge
const TIMESTAMP = { w: 190, h: 90 }; // YouTube draws the video's length in the bottom-right corner

export const Thumbnail: React.FC<ThumbnailProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const { width: W, height: H } = p;

  // The frame: face about faceShare of the height, its middle at a third of the width from its edge, covering all.
  const cover = Math.max(W / p.bgWidth, H / p.bgHeight);
  const scale = Math.max(cover, (p.faceShare * H) / p.faceSize);
  const imgW = p.bgWidth * scale;
  const imgH = p.bgHeight * scale;
  const targetX = p.side === "right" ? W * 0.7 : W * 0.3;
  const left = Math.min(0, Math.max(W - imgW, targetX - p.faceX * scale));
  const top = Math.min(0, Math.max(H - imgH, H * 0.47 - p.faceY * scale));

  // The words: on the other side, in about 55% of the width, never under the timestamp.
  const textW = W * 0.55 - SAFE;
  const longest = Math.max(...p.lines.map((l) => l.length), 1);
  const size = Math.min(p.fontSize, (textW / (longest * 0.7 + 0.4)) | 0, // heavy capitals are about 0.7 em wide
    (H - 2 * SAFE) / (p.lines.length * 1.05 + (p.picture ? 2.2 : 0)));
  const textLeft = p.side === "right" ? SAFE : W - SAFE - textW;
  const fade = p.side === "right" ? "to right" : "to left";

  const word = (w: string, i: number) => {
    const lit = p.highlight && w.replace(/[^\p{L}\p{N}]/gu, "").toLowerCase() === p.highlight.toLowerCase();
    return (
      <span key={i} style={lit ? { color: p.textColor, background: p.accentColor, padding: "0 0.12em", borderRadius: size * 0.12 } : undefined}>
        {w}
      </span>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: p.panelColor, overflow: "hidden" }}>
      <Img src={staticFile(p.background)} style={{ position: "absolute", left, top, width: imgW, height: imgH }} />
      <AbsoluteFill style={{ background: `linear-gradient(${fade}, ${p.panelColor} 0%, ${p.panelColor}E6 38%, ${p.panelColor}00 62%)` }} />
      <div
        style={{
          position: "absolute",
          left: textLeft,
          width: textW,
          top: SAFE,
          bottom: SAFE + (p.side === "left" ? TIMESTAMP.h : 0),
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: p.side === "right" ? "flex-start" : "flex-end",
          gap: size * 0.12,
        }}
      >
        {p.picture ? (
          <Img
            src={staticFile(p.picture)}
            style={{ maxWidth: textW * 0.8, maxHeight: size * 2, objectFit: "contain", borderRadius: 16, border: "6px solid #FFFFFF",
              boxShadow: "0 10px 30px rgba(0,0,0,0.45)", transform: `rotate(${p.side === "right" ? -3 : 3}deg)` }}
          />
        ) : null}
        {p.lines.map((line, li) => (
          <div key={li} style={{ fontFamily: p.font, fontWeight: 900, fontSize: size, lineHeight: 1.02, color: p.textColor,
            textAlign: p.side === "right" ? "left" : "right", WebkitTextStroke: `${Math.max(2, size * 0.035)}px #000000`,
            paintOrder: "stroke fill", textShadow: `0 ${size * 0.06}px ${size * 0.16}px rgba(0,0,0,0.6)`, display: "flex",
            gap: "0.25em", whiteSpace: "nowrap", justifyContent: p.side === "right" ? "flex-start" : "flex-end" }}>
            {line.split(" ").map(word)}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const ThumbnailComposition: React.FC = () => (
  <Still
    id="Thumbnail"
    component={Thumbnail}
    width={1280}
    height={720}
    // Only the required props, empty: Remotion merges these into every render, so samples would leak.
    defaultProps={{ background: "", bgWidth: 1920, bgHeight: 1080, faceX: 0, faceY: 0, faceSize: 1, lines: [] } as ThumbnailProps}
    calculateMetadata={({ props }) => ({ width: props.width ?? 1280, height: props.height ?? 720 })}
  />
);
