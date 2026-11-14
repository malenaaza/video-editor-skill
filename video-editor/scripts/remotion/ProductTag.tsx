// Product lower third: a box with the product name slides in from the side, the price pops
// in on an accent-colored pill, an optional small note sits underneath, and it all slides
// back out at the end. Renders as a short transparent clip; place it with FFmpeg (see SKILL.md).
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it
// in src/Root.tsx:
//   import { ProductTagComposition } from "./ProductTag";
//   ... <ProductTagComposition />
// Render one:
//   npx remotion render src/index.ts ProductTag out/tag-01.mov --codec=prores --prores-profile=4444
//     --pixel-format=yuva444p10le --image-format=png --props=tag-01.json
// Put the props in a JSON file rather than on the command line, so quotes and currency
// symbols survive on Windows. Every prop is optional except name. Match fps, width and
// height to the video the tag goes into.
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ProductTagProps = {
  name: string; // e.g. "Glow Serum"
  price?: string; // e.g. "$24", written the way it should appear
  note?: string; // small line under the name, e.g. "Link in bio"
  font?: string;
  fontFile?: string; // inside public/, e.g. "fonts/Montserrat-Bold.ttf"
  fontSize?: number;
  textColor?: string;
  boxColor?: string;
  accentColor?: string; // price pill
  priceTextColor?: string;
  side?: "left" | "right"; // which edge it slides in from and sits against
  margin?: number; // distance from that edge
  top?: number; // keep it above the caption area saved in my-setup.md
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  font: "sans-serif",
  fontSize: 58,
  textColor: "#FFFFFF",
  boxColor: "#111111",
  accentColor: "#FF4F8B",
  priceTextColor: "#FFFFFF",
  side: "left" as "left" | "right",
  margin: 60,
  top: 1100,
  seconds: 3.5,
  fps: 30,
  width: 1080,
  height: 1920,
};

export const ProductTag: React.FC<ProductTagProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const dir = p.side === "left" ? -1 : 1;
  const slideIn = spring({ frame, fps, config: { damping: 16, mass: 0.7 } });
  const slideOut = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const offset = (1 - slideIn + slideOut) * (p.width * 0.8) * dir;
  const text = spring({ frame: frame - 4, fps, config: { damping: 200 }, durationInFrames: 10 });
  const pop = spring({ frame: frame - 10, fps, config: { damping: 9, mass: 0.5 } });

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: p.top,
          [p.side]: p.margin,
          maxWidth: p.width - p.margin * 2,
          display: "flex",
          alignItems: "center",
          flexDirection: p.side === "left" ? "row" : "row-reverse",
          gap: p.fontSize * 0.3,
          padding: `${p.fontSize * 0.3}px ${p.fontSize * 0.45}px`,
          background: p.boxColor,
          borderRadius: p.fontSize * 0.3,
          boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
          fontFamily: p.font,
          transform: `translateX(${offset}px)`,
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: p.side === "left" ? "flex-start" : "flex-end",
            opacity: text,
            transform: `translateX(${(1 - text) * 30 * dir}px)`,
          }}
        >
          <div style={{ color: p.textColor, fontSize: p.fontSize, fontWeight: 800, lineHeight: 1.1 }}>{p.name}</div>
          {p.note ? (
            <div style={{ color: p.textColor, opacity: 0.8, fontSize: p.fontSize * 0.5, fontWeight: 500, marginTop: 6 }}>
              {p.note}
            </div>
          ) : null}
        </div>
        {p.price ? (
          <div
            style={{
              background: p.accentColor,
              color: p.priceTextColor,
              fontSize: p.fontSize * 0.85,
              fontWeight: 800,
              lineHeight: 1,
              padding: `${p.fontSize * 0.18}px ${p.fontSize * 0.3}px`,
              borderRadius: p.fontSize,
              whiteSpace: "nowrap",
              transform: `scale(${pop}) rotate(${(1 - pop) * -12}deg)`,
            }}
          >
            {p.price}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const ProductTagComposition: React.FC = () => (
  <Composition
    id="ProductTag"
    component={ProductTag}
    durationInFrames={105}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ name: "Glow Serum", price: "$24", note: "Link in bio" } as ProductTagProps}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { durationInFrames: Math.round(p.seconds * p.fps), fps: p.fps, width: p.width, height: p.height };
    }}
  />
);
