// Cover image with the products from the video: a frame of the speaker as the background,
// the title, and the product cutouts placed around the face ("around", the default) or in a
// row ("row", for frames where the face is too big or missing). Numbers, cards, names and
// prices are optional and off by default: names and prices belong in the video (ProductTag).
// For "around", get faceX, faceY and faceSize from scripts/cover/face_box.py.
// Renders a single PNG with `npx remotion still` (see SKILL.md, Cover with products).
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it
// in src/Root.tsx:
//   import { CoverCardComposition } from "./CoverCard";
//   ... <CoverCardComposition />
// Render:
//   npx remotion still src/index.ts CoverCard out/cover.png --props=cover.json
// Image paths are inside the project's public folder: copy the background frame and the
// product cutouts (transparent PNGs from scripts/cover/cutout.py) there first.
import React from "react";
import { AbsoluteFill, Img, Still, staticFile } from "remotion";
import { useBrandFont } from "./brandFont";

type Product = {
  image: string; // inside public/, e.g. "cover/serum-1.png"
  label?: string; // optional, only if asked: short name under the product
  price?: string; // optional, only if asked: written as it should appear
};

export type CoverCardProps = {
  background: string; // frame of the speaker, inside public/, e.g. "cover/frame.png"
  products: Product[]; // 1 to 4
  lines?: string[]; // title lines, e.g. ["3 serums", "I'd buy again"]
  highlight?: string; // a title word in the accent color
  layout?: "around" | "row"; // "around" needs faceX, faceY and faceSize; without them it uses "row"
  faceX?: number; // middle of the face, in pixels of the background frame
  faceY?: number;
  faceSize?: number; // forehead-to-chin height in pixels
  productSize?: number; // "around": size of each product; default about the face's size
  spread?: number; // "around": how far from the face, 1 = default; raise it if products touch the hair
  numbered?: boolean; // 1, 2, 3 badges, only if asked
  cards?: boolean; // a light rounded card behind each product, for busy backgrounds
  font?: string;
  fontFile?: string;
  fontSize?: number;
  textColor?: string;
  boxColor?: string; // title box; "transparent" for none
  accentColor?: string;
  cardColor?: string;
  labelColor?: string;
  dim?: number; // 0 to 1: darken the bottom of the background so products stand out
  titleTop?: number; // leave it out to put the title above the head (needs faceY and faceSize)
  productsTop?: number;
  productHeight?: number;
  width?: number;
  height?: number;
};

const defaults = {
  lines: [] as string[],
  layout: "around" as "around" | "row",
  spread: 1,
  numbered: false,
  cards: false,
  font: "sans-serif",
  fontSize: 104,
  textColor: "#FFFFFF",
  boxColor: "#111111",
  accentColor: "#FF4F8B",
  cardColor: "rgba(255,255,255,0.92)",
  labelColor: "#111111",
  dim: 0,
  productsTop: 1060,
  productHeight: 380,
  width: 1080,
  height: 1920,
};

// Angles around the face for 1 to 4 products: 0 is to the right, 90 straight below.
const ANGLES: Record<number, number[]> = {
  1: [-5],
  2: [185, -5],
  3: [195, -15, 60],
  4: [195, -15, 125, 55],
};

type Box = { cx: number; cy: number; w: number; h: number; tilt: number };

// Medium shot: products beside and slightly below the face.
const besideFace = (n: number, faceX: number, faceY: number, faceSize: number, spread: number,
  size: number | undefined, width: number, safeTop: number, safeBottom: number): Box[] => {
  const angles = ANGLES[Math.max(1, n)] ?? ANGLES[4];
  // Products may overlap the edge of the face and the hair a little.
  const room = Math.min(faceX, width - faceX) - faceSize * 0.4 * spread - 16;
  const scale = n >= 4 ? 0.8 : n === 3 ? 0.95 : 1;
  const w = Math.max(120, Math.min(size ?? faceSize * 1.2 * scale, room * scale));
  const h = w * 1.5;
  const rx = faceSize * 0.4 * spread + w * 0.5;
  const ry = faceSize * 0.8 * spread + h * 0.3;
  return angles.slice(0, n).map((deg) => {
    const a = (deg * Math.PI) / 180;
    const cx = Math.min(width - w / 2 - 16, Math.max(w / 2 + 16, faceX + Math.cos(a) * rx));
    const cy = Math.min(safeBottom - h / 2, Math.max(safeTop + h / 2, faceY + Math.sin(a) * ry));
    return { cx, cy, w, h, tilt: cx < faceX ? 8 : -8 };
  });
};

// Close-up (the face fills the frame): the first two products go in the strips of background
// beside the face, at cheek level, when they're wide enough; the rest go below the chin, over
// the shoulders. With no room beside the face, all go below the chin.
const closeUpLayout = (n: number, faceX: number, faceY: number, faceSize: number, spread: number,
  size: number | undefined, width: number, safeTop: number, safeBottom: number): Box[] => {
  const gap = 16;
  const sideRoom = Math.min(faceX, width - faceX) - faceSize * 0.3 * spread - 16; // may overlap cheek and hair
  const useSides = sideRoom >= 140;
  const sideCount = useSides ? Math.min(n, 2) : 0;
  const boxes: Box[] = [];

  if (sideCount > 0) {
    const w = Math.min(size ?? Infinity, sideRoom, faceSize * 0.9);
    // The strips beside a close-up face are tall, so let tall products (bottles, tubes) use it.
    const h = Math.min(w * 2.2, faceSize * 1.1, safeBottom - safeTop);
    const cy = Math.min(safeBottom - h / 2, Math.max(safeTop + h / 2, faceY));
    const sides = sideCount === 1 ? [1] : [-1, 1];
    for (const side of sides) {
      const cx = side < 0 ? 16 + w / 2 : width - 16 - w / 2;
      boxes.push({ cx, cy, w, h, tilt: side < 0 ? 6 : -6 });
    }
  }

  const below = n - sideCount;
  if (below > 0) {
    const chin = faceY + faceSize * 0.42 * spread; // may overlap the chin a little
    const maxH = safeBottom - chin - 10;
    const w = Math.min(size ?? Infinity, (width - 32 - gap * (below - 1)) / below, maxH / 1.5, faceSize * 0.9);
    const h = Math.min(w * 1.5, maxH);
    const rowWidth = below * w + (below - 1) * gap;
    const left = (width - rowWidth) / 2;
    for (let i = 0; i < below; i++) {
      const cx = left + w / 2 + i * (w + gap);
      boxes.push({ cx, cy: chin + 10 + h / 2, w, h, tilt: cx < faceX ? 4 : -4 });
    }
  }
  return boxes;
};

const AroundFace: React.FC<{
  products: Product[];
  faceX: number;
  faceY: number;
  faceSize: number;
  size?: number;
  spread: number;
  width: number;
  height: number;
  numbered: boolean;
  accentColor: string;
  titleTop?: number; // a title below the face: products stay above it
  minTop?: number; // a title above the face: products stay below it
}> = ({ products, faceX, faceY, faceSize, size, spread, width, height, numbered, accentColor, titleTop, minTop }) => {
  // Keep products inside the middle 3:4 of the frame, which profile grids show,
  // and above a title placed below the face.
  const gridTop = (height - (width * 4) / 3) / 2;
  const safeTop = Math.max(gridTop, minTop ?? 0);
  const safeBottom = Math.min(height - gridTop, titleTop !== undefined && titleTop > faceY ? titleTop - 20 : Infinity);
  const room = Math.min(faceX, width - faceX) - faceSize * 0.55 * spread - 16;
  const closeUp = room < faceSize * 0.45;
  const boxes = closeUp
    ? closeUpLayout(products.length, faceX, faceY, faceSize, spread, size, width, safeTop, safeBottom)
    : besideFace(products.length, faceX, faceY, faceSize, spread, size, width, safeTop, safeBottom);
  return (
    <>
      {products.map((product, i) => {
        const { cx, cy, w, h, tilt } = boxes[i];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: cx - w / 2,
              top: cy - h / 2,
              width: w,
              height: h,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transform: `rotate(${tilt}deg)`,
            }}
          >
            <Img
              src={staticFile(product.image)}
              style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                filter: "drop-shadow(0 14px 18px rgba(0,0,0,0.35))",
              }}
            />
            {numbered ? (
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: 70,
                  height: 70,
                  borderRadius: 35,
                  background: accentColor,
                  color: "#FFFFFF",
                  fontSize: 42,
                  fontWeight: 800,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {i + 1}
              </div>
            ) : null}
          </div>
        );
      })}
    </>
  );
};

const clean = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

export const CoverCard: React.FC<CoverCardProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const count = Math.max(1, Math.min(p.products.length, 4));
  const gap = 28;
  const slot = Math.min((p.width - 80 - gap * (count - 1)) / count, p.productHeight * 0.9);
  const around =
    p.layout === "around" && p.faceX !== undefined && p.faceY !== undefined && p.faceSize !== undefined;
  // Without titleTop, the title sits above the head, its bottom on the top of the hair. If there
  // isn't room, it starts at the top of the grid crop and runs over the head.
  const safeTop = (p.height - (p.width * 4) / 3) / 2;
  const titleHeight = p.lines.length * p.fontSize * 1.26 + Math.max(0, p.lines.length - 1) * p.fontSize * 0.12;
  const titleTop =
    p.titleTop ??
    (p.faceY !== undefined && p.faceSize !== undefined
      ? Math.max(safeTop + 10, p.faceY - p.faceSize * 0.62 - titleHeight)
      : safeTop + 90);
  const titlePosition: React.CSSProperties = { top: titleTop };
  // A title above the face pushes the products below it.
  const productsMinTop =
    p.lines.length > 0 && p.faceY !== undefined && titleTop < p.faceY ? titleTop + titleHeight + 10 : undefined;

  return (
    <AbsoluteFill style={{ fontFamily: p.font }}>
      <Img src={staticFile(p.background)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill
        style={{ background: `linear-gradient(to bottom, rgba(0,0,0,0) 40%, rgba(0,0,0,${p.dim}) 100%)` }}
      />


      {around ? (
        <AroundFace
          products={p.products.slice(0, 4)}
          faceX={p.faceX as number}
          faceY={p.faceY as number}
          faceSize={p.faceSize as number}
          size={p.productSize}
          spread={p.spread}
          width={p.width}
          height={p.height}
          numbered={p.numbered}
          accentColor={p.accentColor}
          titleTop={p.lines.length > 0 ? titleTop : undefined}
          minTop={productsMinTop}
        />
      ) : (
      <div
        style={{
          position: "absolute",
          top: p.productsTop,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-end",
          gap,
        }}
      >
        {p.products.slice(0, 4).map((product, i) => (
          <div key={i} style={{ width: slot, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                position: "relative",
                width: slot,
                height: p.productHeight,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: p.cards ? p.cardColor : "transparent",
                borderRadius: 32,
                boxShadow: p.cards ? "0 12px 30px rgba(0,0,0,0.25)" : undefined,
              }}
            >
              <Img
                src={staticFile(product.image)}
                style={{
                  maxWidth: "86%",
                  maxHeight: "86%",
                  objectFit: "contain",
                  filter: "drop-shadow(0 10px 14px rgba(0,0,0,0.3))",
                }}
              />
              {p.numbered ? (
                <div
                  style={{
                    position: "absolute",
                    top: -22,
                    left: -10,
                    width: 76,
                    height: 76,
                    borderRadius: 38,
                    background: p.accentColor,
                    color: "#FFFFFF",
                    fontSize: 46,
                    fontWeight: 800,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "0 6px 14px rgba(0,0,0,0.25)",
                  }}
                >
                  {i + 1}
                </div>
              ) : null}
              {product.price ? (
                <div
                  style={{
                    position: "absolute",
                    bottom: -20,
                    right: -8,
                    background: p.accentColor,
                    color: "#FFFFFF",
                    fontSize: 40,
                    fontWeight: 800,
                    padding: "8px 18px",
                    borderRadius: 40,
                    whiteSpace: "nowrap",
                    boxShadow: "0 6px 14px rgba(0,0,0,0.25)",
                  }}
                >
                  {product.price}
                </div>
              ) : null}
            </div>
            {product.label ? (
              <div
                style={{
                  marginTop: 34,
                  background: p.cards ? p.cardColor : "transparent",
                  color: p.cards ? p.labelColor : p.textColor,
                  fontSize: 36,
                  fontWeight: 700,
                  padding: "6px 16px",
                  borderRadius: 18,
                  textAlign: "center",
                  maxWidth: slot + 20,
                }}
              >
                {product.label}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      )}
      {/* The title goes last, so it's drawn on top of everything. */}
      {p.lines.length > 0 ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: p.fontSize * 0.12,
            ...titlePosition,
          }}
        >
          {p.lines.map((line, li) => (
            <div
              key={li}
              style={{
                background: p.boxColor,
                borderRadius: p.fontSize * 0.18,
                padding: `${p.fontSize * 0.08}px ${p.fontSize * 0.3}px`,
                maxWidth: p.width - 120,
                textAlign: "center",
                fontSize: p.fontSize,
                fontWeight: 800,
                lineHeight: 1.1,
                color: p.textColor,
              }}
            >
              {line.split(" ").map((word, wi, words) => (
                <span
                  key={wi}
                  style={{
                    color: p.highlight !== undefined && clean(word) === clean(p.highlight) ? p.accentColor : undefined,
                  }}
                >
                  {word}
                  {wi < words.length - 1 ? " " : ""}
                </span>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const CoverCardComposition: React.FC = () => (
  <Still
    id="CoverCard"
    component={CoverCard}
    width={1080}
    height={1920}
    defaultProps={
      {
        background: "cover/frame.png",
        products: [{ image: "cover/product-1.png" }],
      } as CoverCardProps
    }
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { width: p.width, height: p.height };
    }}
  />
);
