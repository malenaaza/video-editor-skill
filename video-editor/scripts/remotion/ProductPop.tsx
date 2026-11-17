// Product pop-in: when the speaker names a product, its B-roll photo (cut out) or a short muted clip in a rounded
// card pops in beside them with a spring, a slight tilt and a soft shadow, floats gently, and pops out. An optional
// name and price sit underneath, so it can replace a separate ProductTag for that moment. Renders as a short
// transparent clip; place it with FFmpeg like the emojis (see references/graphics.md), with pop.wav on its first frame.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, copy the picture or clip into public/,
// then register it in src/Root.tsx:
//   import { ProductPopComposition } from "./ProductPop";
//   ... <ProductPopComposition />
// Render one:
//   npx remotion render src/index.ts ProductPop out/pop-01.mov --codec=prores --prores-profile=4444
//     --pixel-format=yuva444p10le --image-format=png --props=pop-01.json
// Put the props in a JSON file. Give either image (a cut-out PNG from cover/cutout.py) or clip. Match fps,
// width and height to the video it goes into.
import React from "react";
import {
  AbsoluteFill,
  Composition,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useBrandFont } from "./brandFont";

export type ProductPopProps = {
  image?: string; // inside public/, e.g. "products/glow-serum.png" (a cut-out with a transparent background)
  clip?: string; // inside public/, e.g. "broll/labial-swatch.mp4" (shown muted, in a rounded card)
  clipStart?: number; // seconds into the clip where the moment starts
  name?: string; // optional, e.g. "Glow Serum"
  price?: string; // optional, written the way it should appear; never guessed
  note?: string; // optional small line, e.g. "Link in bio"
  side?: "left" | "right"; // the side away from the face
  top?: number; // keep the whole pop-in above the caption area saved in my-setup.md
  margin?: number; // distance from that edge
  size?: number; // width of the picture or card, in pixels
  font?: string;
  fontFile?: string; // inside public/, e.g. "fonts/Montserrat-Bold.ttf"
  fontSize?: number;
  textColor?: string;
  boxColor?: string; // behind the name
  accentColor?: string; // price pill
  cardColor?: string; // the clip card's border
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  clipStart: 0,
  side: "right" as "left" | "right",
  top: 520,
  margin: 50,
  size: 360,
  font: "sans-serif",
  fontSize: 46,
  textColor: "#FFFFFF",
  boxColor: "#111111",
  accentColor: "#FF4F8B",
  cardColor: "#FFFFFF",
  seconds: 2.6,
  fps: 30,
  width: 1080,
  height: 1920,
};

export const ProductPop: React.FC<ProductPopProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const pop = spring({ frame, fps, config: { damping: 9, mass: 0.6 } });
  const leave = interpolate(frame, [durationInFrames - 7, durationInFrames - 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = pop * (0.6 + 0.4 * leave);
  const lean = p.side === "right" ? 1 : -1;
  const tilt = lean * (4 + (1 - pop) * 10) + Math.sin(frame / 9) * 1.2;
  const bob = Math.sin(frame / 11) * 6;
  const label = spring({ frame: frame - 6, fps, config: { damping: 200 }, durationInFrames: 10 });

  const picture = p.clip ? (
    <div
      style={{
        width: p.size,
        aspectRatio: "9 / 16",
        borderRadius: p.size * 0.08,
        overflow: "hidden",
        border: `${Math.round(p.size * 0.025)}px solid ${p.cardColor}`,
        boxShadow: "0 18px 40px rgba(0,0,0,0.35)",
        background: "#000",
      }}
    >
      <OffthreadVideo
        src={staticFile(p.clip)}
        startFrom={Math.round(p.clipStart * fps)}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </div>
  ) : p.image ? (
    <Img
      src={staticFile(p.image)}
      style={{ width: p.size, height: "auto", filter: "drop-shadow(0 16px 22px rgba(0,0,0,0.35))" }}
    />
  ) : null;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: p.top + bob,
          [p.side]: p.margin,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: p.fontSize * 0.3,
          opacity: leave,
          transform: `scale(${scale}) rotate(${tilt}deg)`,
          transformOrigin: "center bottom",
          fontFamily: p.font,
        }}
      >
        {picture}
        {p.name ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: p.fontSize * 0.25,
              padding: `${p.fontSize * 0.22}px ${p.fontSize * 0.4}px`,
              background: p.boxColor,
              borderRadius: p.fontSize * 0.3,
              boxShadow: "0 8px 20px rgba(0,0,0,0.25)",
              opacity: label,
              transform: `translateY(${(1 - label) * 20}px) rotate(${-tilt * 0.6}deg)`,
              maxWidth: p.size * 1.4,
            }}
          >
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ color: p.textColor, fontSize: p.fontSize, fontWeight: 800, lineHeight: 1.1 }}>{p.name}</div>
              {p.note ? (
                <div style={{ color: p.textColor, opacity: 0.8, fontSize: p.fontSize * 0.5, marginTop: 4 }}>{p.note}</div>
              ) : null}
            </div>
            {p.price ? (
              <div
                style={{
                  background: p.accentColor,
                  color: p.textColor,
                  fontSize: p.fontSize * 0.8,
                  fontWeight: 800,
                  lineHeight: 1,
                  padding: `${p.fontSize * 0.16}px ${p.fontSize * 0.28}px`,
                  borderRadius: p.fontSize,
                  whiteSpace: "nowrap",
                }}
              >
                {p.price}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const ProductPopComposition: React.FC = () => (
  <Composition
    id="ProductPop"
    component={ProductPop}
    durationInFrames={78}
    fps={30}
    width={1080}
    height={1920}
    // No sample values here: Remotion merges these into every render, so a sample name would leak into real ones.
    defaultProps={{} as ProductPopProps}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { durationInFrames: Math.round(p.seconds * p.fps), fps: p.fps, width: p.width, height: p.height };
    }}
  />
);
