// A real web page in a browser window for educational videos: the screenshot scrolls to where the speaker is, and
// boxes highlight what they mention. Times, scroll stops and boxes come from `overlays.py browser`, so this file only
// draws: never edit it for one video. Use a public page's own screenshot (references/graphics.md, Web page).
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { BrowserPageComposition } from "./BrowserPage";
//   ... <BrowserPageComposition />
// Render: npx remotion render src/index.ts BrowserPage out/browser.mov --props=browser-props.json
import React from "react";
import { AbsoluteFill, Composition, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type BrowserPageProps = {
  image: string;
  url?: string;
  pageWidth: number;
  pageHeight: number;
  scroll: { frame: number; to: number }[];
  boxes: { frame: number; x: number; y: number; w: number; h: number }[];
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
  url: "", fontSize: 54, accentColor: "#FF4F8B", font: "sans-serif", fontFile: "", background: "#1B1033",
  background2: "#0E2A47", seconds: 6, fps: 30, width: 1920, height: 1080,
};

export const BrowserPage: React.FC<BrowserPageProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = p.fontSize;
  const vertical = p.height > p.width;
  const winW = vertical ? p.width * 0.9 : p.width * 0.8;
  const winH = vertical ? p.height * 0.7 : p.height * 0.84;
  const bar = s * 1.4;
  const viewH = winH - bar;
  const scale = winW / p.pageWidth;
  const maxScroll = Math.max(0, p.pageHeight * scale - viewH);
  const stops = p.scroll.length ? p.scroll : [{ frame: 0, to: 0 }];
  let to = stops[0].to;
  for (let i = 1; i < stops.length; i++) {
    const a = stops[i - 1], b = stops[i];
    if (frame >= b.frame) to = b.to;
    else if (frame >= b.frame - Math.round(fps * 0.9) && frame >= a.frame) {
      to = interpolate(frame, [b.frame - Math.round(fps * 0.9), b.frame], [a.to, b.to],
        { easing: Easing.inOut(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      break;
    } else break;
  }
  const y = to * maxScroll;
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 140 } });
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const over = p.background === "transparent";
  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center",
      background: over ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div style={{ width: winW, height: winH, borderRadius: s * 0.5, overflow: "hidden", backgroundColor: "#FFFFFF",
        boxShadow: "0 30px 80px rgba(0,0,0,0.35)", transform: `scale(${0.92 + 0.08 * enter})`, opacity: Math.min(1, enter * 1.4) * leave }}>
        <div style={{ height: bar, display: "flex", alignItems: "center", gap: s * 0.25, padding: `0 ${s * 0.5}px`,
          backgroundColor: "#ECECF1", borderBottom: "2px solid #DADAE2" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
            <div key={c} style={{ width: s * 0.32, height: s * 0.32, borderRadius: s, backgroundColor: c }} />
          ))}
          <div style={{ flex: 1, marginLeft: s * 0.4, height: bar * 0.6, borderRadius: bar, backgroundColor: "#FFFFFF",
            display: "flex", alignItems: "center", padding: `0 ${s * 0.4}px`, color: "#55555F", fontSize: s * 0.45,
            whiteSpace: "nowrap", overflow: "hidden" }}>
            {p.url}
          </div>
        </div>
        <div style={{ position: "relative", height: viewH, overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, top: -y, width: winW }}>
            <Img src={staticFile(p.image)} style={{ width: winW, display: "block" }} />
            {p.boxes.map((b, i) => {
              if (frame < b.frame) return null;
              const pop = spring({ frame: frame - b.frame, fps, config: { damping: 14, stiffness: 160 } });
              return (
                <div key={i} style={{ position: "absolute", left: b.x * scale - 6, top: b.y * scale - 6,
                  width: b.w * scale + 12, height: b.h * scale + 12, borderRadius: s * 0.2,
                  border: `${Math.max(4, s / 10)}px solid ${p.accentColor}`, backgroundColor: `${p.accentColor}22`,
                  transform: `scale(${0.9 + 0.1 * pop})`, opacity: pop }} />
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const BrowserPageComposition: React.FC = () => (
  <Composition id="BrowserPage" component={BrowserPage} durationInFrames={180} fps={30} width={1920} height={1080}
    defaultProps={{ image: "", pageWidth: 1440, pageHeight: 3000, scroll: [], boxes: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
