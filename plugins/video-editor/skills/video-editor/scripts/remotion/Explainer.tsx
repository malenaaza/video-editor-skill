// Animated explanation for part of an educational video: coloured boxes, arrows and a dot that travels between
// them, each appearing at its own frame. Every position, colour and time comes from scripts/explainer.py, which
// reads explainer.json and the captions, so this file only draws: never edit it for one video.
//   - the background is a soft gradient with a faint dot grid (or transparent, to lay it over the speaker);
//   - the title rises in, and a line in the accent colour grows under it;
//   - a box pops in (a small spring) in its own colour, with its label and an optional emoji before it, inside the
//     box (above it the emoji ran into the arrows of a vertical diagram);
//   - an arrow draws itself, then its head and label appear, and short dashes keep moving along it, showing the
//     direction things travel;
//   - a flow sends a glowing accent dot with a short trail along a path of boxes (there and back, for a request
//     and its answer), and each box it reaches lights up;
//   - everything fades out in the last 8 frames.
// A first version with a flat background, white boxes and white lines looked dull: colour does the explaining.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ExplainerComposition } from "./Explainer";
//   ... <ExplainerComposition />
// Render one (props from explainer.py, in a file so accents and emoji survive on Windows):
//   npx remotion render src/index.ts Explainer out/explainer.mov --props=explainer-props.json
import React from "react";
import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ExplainerNode = {
  id: string; label: string; icon?: string; color: string; textColor: string;
  x: number; y: number; w: number; h: number; frame: number;
};
export type ExplainerLink = {
  from: string; to: string; label?: string; both?: boolean;
  x1: number; y1: number; x2: number; y2: number; frame: number; frames: number;
};
export type ExplainerFlow = { points: [number, number][]; frame: number; frames: number };

export type ExplainerProps = {
  title?: string;
  nodes: ExplainerNode[];
  links: ExplainerLink[];
  flows: ExplainerFlow[];
  fontSize?: number;
  labelSide?: "above" | "right"; // arrow labels above the line (boxes in a row) or beside it (in a column)
  font?: string;
  fontFile?: string; // inside public/, e.g. "fonts/Montserrat-Bold.ttf"
  background?: string; // "transparent" to lay it over the speaker
  background2?: string; // the other end of the gradient
  accentColor?: string;
  lineColor?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  title: "",
  fontSize: 60,
  labelSide: "above" as "above" | "right",
  font: "sans-serif",
  fontFile: "",
  background: "#1B1033",
  background2: "#0E2A47",
  accentColor: "#FF4F8B",
  lineColor: "#FFFFFF",
  seconds: 6,
  fps: 30,
  width: 1920,
  height: 1080,
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Where the dot is after `t` (0 to 1) of the way along a path of points, at an even speed.
const along = (points: [number, number][], t: number): [number, number] => {
  const lengths = points.slice(1).map((p, i) => Math.hypot(p[0] - points[i][0], p[1] - points[i][1]));
  const total = lengths.reduce((a, b) => a + b, 0) || 1;
  let left = Math.min(Math.max(t, 0), 1) * total;
  for (let i = 0; i < lengths.length; i++) {
    if (left <= lengths[i] || i === lengths.length - 1) {
      const k = lengths[i] ? Math.min(left / lengths[i], 1) : 1;
      return [points[i][0] + (points[i + 1][0] - points[i][0]) * k, points[i][1] + (points[i + 1][1] - points[i][1]) * k];
    }
    left -= lengths[i];
  }
  return points[points.length - 1];
};

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

export const Explainer: React.FC<ExplainerProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const fadeOut = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], clamp);
  const stroke = Math.max(4, Math.round(p.fontSize / 9));
  const head = stroke * 3.2;
  const overSpeaker = p.background === "transparent";
  const textOnBackground = overSpeaker ? "#FFFFFF" : p.lineColor;

  // A box lights up while a flow's dot is on it.
  const lit = (node: ExplainerNode) =>
    p.flows.some((f) => {
      if (frame < f.frame || frame > f.frame + f.frames + 6) return false;
      const [dx, dy] = along(f.points, ease((frame - f.frame) / f.frames));
      return Math.hypot(dx - node.x, dy - node.y) < Math.max(node.w, node.h) * 0.45;
    });

  const titleIn = interpolate(frame, [0, 10], [0, 1], clamp);
  const underline = interpolate(frame, [6, 22], [0, 1], clamp);

  return (
    <AbsoluteFill
      style={{
        fontFamily: p.font,
        background: overSpeaker ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)`,
      }}
    >
      {overSpeaker ? null : (
        <AbsoluteFill
          style={{
            backgroundImage: `radial-gradient(${p.lineColor} 1.5px, transparent 1.5px)`,
            backgroundSize: `${p.fontSize * 0.8}px ${p.fontSize * 0.8}px`,
            opacity: 0.07,
          }}
        />
      )}
      <AbsoluteFill style={{ opacity: fadeOut }}>
        {p.title ? (
          <div
            style={{
              position: "absolute", top: p.height * 0.07, width: "100%", display: "flex", flexDirection: "column",
              alignItems: "center", opacity: titleIn, transform: `translateY(${(1 - titleIn) * 20}px)`,
            }}
          >
            <div style={{ color: textOnBackground, fontSize: p.fontSize * 1.05, fontWeight: 800,
              textShadow: overSpeaker ? "0 3px 12px rgba(0,0,0,0.6)" : "none" }}>
              {p.title}
            </div>
            <div style={{ marginTop: p.fontSize * 0.25, height: stroke * 1.4, borderRadius: stroke,
              width: p.fontSize * 3 * underline, backgroundColor: p.accentColor }} />
          </div>
        ) : null}

        <svg width={p.width} height={p.height} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
          <defs>
            <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation={p.fontSize * 0.18} result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          {p.links.map((l, i) => {
            const drawn = interpolate(frame, [l.frame, l.frame + l.frames], [0, 1], clamp);
            if (drawn <= 0) return null;
            const len = Math.hypot(l.x2 - l.x1, l.y2 - l.y1) || 1;
            const ux = (l.x2 - l.x1) / len;
            const uy = (l.y2 - l.y1) / len;
            const headIn = interpolate(frame, [l.frame + l.frames - 3, l.frame + l.frames + 3], [0, 1], clamp);
            const arrow = (x: number, y: number, dx: number, dy: number) => (
              <polygon
                points={`${x},${y} ${x - dx * head - dy * head * 0.6},${y - dy * head + dx * head * 0.6} ${x - dx * head + dy * head * 0.6},${y - dy * head - dx * head * 0.6}`}
                fill={p.lineColor} opacity={headIn}
              />
            );
            const sx = l.x1 + (l.both ? ux * head * 0.8 * headIn : 0);
            const sy = l.y1 + (l.both ? uy * head * 0.8 * headIn : 0);
            const ex = l.x1 + (l.x2 - l.x1) * drawn - ux * head * 0.8 * headIn;
            const ey = l.y1 + (l.y2 - l.y1) * drawn - uy * head * 0.8 * headIn;
            const dash = stroke * 2.2;
            return (
              <g key={`l${i}`}>
                <line x1={sx} y1={sy} x2={ex} y2={ey} stroke={p.lineColor} strokeOpacity={0.45}
                  strokeWidth={stroke} strokeLinecap="round" />
                {headIn > 0 ? (
                  <line x1={sx} y1={sy} x2={ex} y2={ey} stroke={p.accentColor} strokeWidth={stroke}
                    strokeLinecap="round" strokeDasharray={`${dash} ${dash * 1.6}`}
                    strokeDashoffset={-(frame - l.frame) * stroke * 0.9} opacity={headIn} />
                ) : null}
                {arrow(l.x2, l.y2, ux, uy)}
                {l.both ? arrow(l.x1, l.y1, -ux, -uy) : null}
              </g>
            );
          })}
          {p.flows.map((f, i) => {
            if (frame < f.frame || frame > f.frame + f.frames + 6) return null;
            const t = interpolate(frame, [f.frame, f.frame + f.frames], [0, 1], clamp);
            const show = interpolate(frame, [f.frame, f.frame + 4, f.frame + f.frames + 2, f.frame + f.frames + 6], [0, 1, 1, 0], clamp);
            const r = p.fontSize * 0.3;
            return (
              <g key={`f${i}`} opacity={show}>
                {[4, 3, 2, 1].map((k) => {
                  const [tx, ty] = along(f.points, ease(Math.max(0, t - k * 0.012)));
                  return <circle key={k} cx={tx} cy={ty} r={r * (1 - k * 0.16)} fill={p.accentColor} opacity={0.5 - k * 0.1} />;
                })}
                {(() => {
                  const [x, y] = along(f.points, ease(t));
                  return <circle cx={x} cy={y} r={r} fill={p.accentColor} stroke="#FFFFFF" strokeWidth={stroke * 0.6} filter="url(#glow)" />;
                })()}
              </g>
            );
          })}
        </svg>

        {p.links.map((l, i) =>
          l.label ? (
            <div
              key={`ll${i}`}
              style={{
                position: "absolute", fontSize: p.fontSize * 0.55, fontWeight: 700, whiteSpace: "nowrap",
                color: textOnBackground, textShadow: overSpeaker ? "0 2px 8px rgba(0,0,0,0.7)" : "none",
                ...(p.labelSide === "right"
                  ? { left: (l.x1 + l.x2) / 2 + p.fontSize * 0.5, top: (l.y1 + l.y2) / 2 - p.fontSize * 0.4, textAlign: "left" as const }
                  : { left: (l.x1 + l.x2) / 2 - 300, width: 600, top: (l.y1 + l.y2) / 2 - p.fontSize * 1.05, textAlign: "center" as const }),
                opacity: interpolate(frame, [l.frame + l.frames - 2, l.frame + l.frames + 6], [0, 1], clamp),
              }}
            >
              {l.label}
            </div>
          ) : null,
        )}

        {p.nodes.map((n) => {
          if (frame < n.frame) return null;
          const pop = spring({ frame: frame - n.frame, fps, config: { damping: 12, stiffness: 160 } });
          const on = lit(n);
          return (
            <div
              key={n.id}
              style={{
                position: "absolute", left: n.x - n.w / 2, top: n.y - n.h / 2, width: n.w, height: n.h,
                display: "flex", alignItems: "center", justifyContent: "center",
                backgroundColor: n.color, color: n.textColor, borderRadius: n.h * 0.3,
                border: `${stroke}px solid ${on ? "#FFFFFF" : "rgba(255,255,255,0.25)"}`,
                boxShadow: on
                  ? `0 0 ${p.fontSize * 1.1}px ${n.color}, 0 0 ${p.fontSize * 0.4}px #FFFFFF`
                  : `0 ${stroke * 1.5}px ${stroke * 5}px ${n.color}66`,
                fontSize: p.fontSize, fontWeight: 800, transform: `scale(${pop * (on ? 1.06 : 1)})`,
                opacity: Math.min(1, pop * 1.5),
              }}
            >
              {n.icon ? <span style={{ marginRight: p.fontSize * 0.3 }}>{n.icon}</span> : null}
              {n.label}
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const ExplainerComposition: React.FC = () => (
  <Composition
    id="Explainer"
    component={Explainer}
    durationInFrames={180}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ nodes: [], links: [], flows: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return {
        fps: p.fps,
        width: p.width,
        height: p.height,
        durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)),
      };
    }}
  />
);
