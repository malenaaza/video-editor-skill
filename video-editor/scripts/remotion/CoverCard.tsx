// Cover image with the products from the video: a frame of the speaker as the background,
// the title, and a row of product cutouts, optionally numbered. Names and prices are
// optional and off by default: they belong in the video (ProductTag), not on the cover.
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
  numbered?: boolean; // 1, 2, 3 badges, for ranking and "3 things" videos
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
  titleTop?: number; // keep the title and products inside the platform's grid crop
  productsTop?: number;
  productHeight?: number;
  width?: number;
  height?: number;
};

const defaults = {
  lines: [] as string[],
  numbered: false,
  cards: true,
  font: "sans-serif",
  fontSize: 104,
  textColor: "#FFFFFF",
  boxColor: "#111111",
  accentColor: "#FF4F8B",
  cardColor: "rgba(255,255,255,0.92)",
  labelColor: "#111111",
  dim: 0.35,
  titleTop: 330,
  productsTop: 1060,
  productHeight: 380,
  width: 1080,
  height: 1920,
};

const clean = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

export const CoverCard: React.FC<CoverCardProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile);
  const count = Math.max(1, Math.min(p.products.length, 4));
  const gap = 28;
  const slot = Math.min((p.width - 80 - gap * (count - 1)) / count, p.productHeight * 0.9);

  return (
    <AbsoluteFill style={{ fontFamily: p.font }}>
      <Img src={staticFile(p.background)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill
        style={{ background: `linear-gradient(to bottom, rgba(0,0,0,0) 40%, rgba(0,0,0,${p.dim}) 100%)` }}
      />

      {p.lines.length > 0 ? (
        <div
          style={{
            position: "absolute",
            top: p.titleTop,
            left: 0,
            right: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: p.fontSize * 0.12,
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
        lines: ["My new favorite"],
      } as CoverCardProps
    }
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { width: p.width, height: p.height };
    }}
  />
);
