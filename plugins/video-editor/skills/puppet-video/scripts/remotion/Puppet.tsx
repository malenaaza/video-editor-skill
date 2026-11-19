// Puppet video: one or two characters, drawn here in code, saying the turns of a dialogue with the right mouth shape
// for each sound, blinking, breathing, leaning in when they talk and looking at whoever speaks.
// The props come from scripts/dialogue.py (puppet-props.json): characters, turns with times, mouth shapes and
// expressions, and the length. Copy voice.wav into the Remotion project's public folder and add "audio": "voice.wav".
//
// Characters (look): "lola" (a round, warm creature with a tuft), "max" (a tall, calm one with glasses) and "pixel"
// (a small robot for AI topics). "colour" recolours one. Every character is one component with the same props
// (mouth, blink, look, expression), so a drawn character can replace one later without touching the rest.
//
// Copy this file into the Remotion project's src folder and register it in src/Root.tsx:
//   import { PuppetComposition } from "./Puppet";
//   ... <PuppetComposition />
// Render:
//   npx remotion render src/index.ts Puppet out/puppet.mp4 --props=puppet-props.json
// Captions: transcribe voice.wav and make them with the video editor's captions.py (see SKILL.md); with
// "showTranslation": true each turn's translation is written under them, for students.
import React from "react";
import { AbsoluteFill, Audio, Composition, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export type Shape = "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "X";
export type Expression = "neutral" | "happy" | "surprised" | "thinking" | "sad";
export type Look = "lola" | "max" | "pixel";

export type PuppetTurn = {
  speaker: string;
  text: string;
  translation?: string | null;
  expression?: Expression;
  start: number; // seconds
  end: number;
  mouth: [number, Shape][]; // [time in seconds, shape], each holds until the next
};

export type PuppetProps = {
  characters: { name: string; look: Look; colour?: string | null }[];
  turns: PuppetTurn[];
  length?: number;
  audio?: string; // inside public/, e.g. "voice.wav"
  background?: string; // inside public/: an image instead of the colours
  bgTop?: string;
  bgBottom?: string;
  floor?: string;
  showTranslation?: boolean;
  translationColor?: string;
  font?: string;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  bgTop: "#FFE3EC",
  bgBottom: "#FFC2D4",
  floor: "rgba(255,255,255,0.45)",
  showTranslation: false,
  translationColor: "#3A2340",
  font: "sans-serif",
  fps: 30,
  width: 1080,
  height: 1920,
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const INK = "#2B1B2E";

// ---- the face parts, shared by every character ---------------------------------------------------------------------

type FaceState = { shape: Shape; blink: number; lookX: number; lookY: number; expression: Expression; talk: number };

const Mouth: React.FC<{ shape: Shape; expression: Expression; x: number; y: number; ink?: string; inside?: string }> = ({
  shape, expression, x, y, ink = INK, inside = "#5A1E2E" }) => {
  const teeth = "#FFFFFF";
  const tongue = "#FF7A8A";
  let body: React.ReactNode;
  switch (shape) {
    case "A": // m, b, p: lips pressed
      body = <path d="M-26,0 L26,0" stroke={ink} strokeWidth={8} strokeLinecap="round" />;
      break;
    case "B": // most consonants: slightly open, teeth showing
      body = (<g><rect x={-26} y={-8} width={52} height={16} rx={8} fill={inside} />
        <rect x={-22} y={-8} width={44} height={6} rx={3} fill={teeth} /></g>);
      break;
    case "C": // e, eh: open
      body = (<g><ellipse cx={0} cy={2} rx={27} ry={15} fill={inside} />
        <rect x={-20} y={-12} width={40} height={6} rx={3} fill={teeth} /></g>);
      break;
    case "D": // a, ah: wide open
      body = (<g><ellipse cx={0} cy={6} rx={31} ry={25} fill={inside} />
        <ellipse cx={0} cy={20} rx={18} ry={9} fill={tongue} />
        <rect x={-22} y={-18} width={44} height={7} rx={3} fill={teeth} /></g>);
      break;
    case "E": // o: rounded
      body = <ellipse cx={0} cy={4} rx={18} ry={19} fill={inside} stroke={ink} strokeWidth={3} />;
      break;
    case "F": // oo, w: puckered
      body = <ellipse cx={0} cy={2} rx={10} ry={12} fill={inside} stroke={ink} strokeWidth={5} />;
      break;
    case "G": // f, v: upper teeth on the lower lip
      body = (<g><ellipse cx={0} cy={2} rx={24} ry={10} fill={inside} />
        <rect x={-18} y={-6} width={36} height={10} rx={3} fill={teeth} /></g>);
      break;
    case "H": // l: open, tongue up
      body = (<g><ellipse cx={0} cy={4} rx={26} ry={18} fill={inside} />
        <ellipse cx={0} cy={-4} rx={12} ry={7} fill={tongue} /></g>);
      break;
    default: { // X: at rest, shaped by the expression
      const curve = expression === "happy" ? 16 : expression === "sad" ? -10 : expression === "surprised" ? 0 : 7;
      body = expression === "surprised"
        ? <ellipse cx={0} cy={2} rx={10} ry={12} fill={inside} stroke={ink} strokeWidth={3} />
        : <path d={`M-28,0 Q0,${curve} 28,0`} stroke={ink} strokeWidth={6} fill="none" strokeLinecap="round" />;
    }
  }
  return <g transform={`translate(${x},${y})`}>{body}</g>;
};

const Eye: React.FC<{ x: number; y: number; rx: number; ry: number; s: FaceState; lid: string }> = ({ x, y, rx, ry, s, lid }) => {
  const grow = s.expression === "surprised" ? 1.15 : 1;
  const r = ry * grow;
  const lidH = r * 2 * s.blink;
  return (
    <g>
      <ellipse cx={x} cy={y} rx={rx * grow} ry={r} fill="#FFFFFF" stroke={INK} strokeWidth={3} />
      <circle cx={x + s.lookX * rx * 0.35} cy={y + s.lookY * r * 0.35} r={rx * 0.42} fill={INK} />
      <circle cx={x + s.lookX * rx * 0.35 + rx * 0.14} cy={y + s.lookY * r * 0.35 - rx * 0.16} r={rx * 0.13} fill="#FFFFFF" />
      {s.blink > 0.02 ? (
        <rect x={x - rx * grow - 3} y={y - r - 3} width={rx * grow * 2 + 6} height={lidH + 3} rx={rx * 0.6} fill={lid} />
      ) : null}
    </g>
  );
};

const Brows: React.FC<{ lx: number; rx: number; y: number; w: number; s: FaceState; colour?: string }> = ({ lx, rx, y, w, s, colour = INK }) => {
  const up = s.expression === "surprised" ? 18 : s.expression === "happy" ? 7 : 0;
  const tilt = s.expression === "sad" ? -10 : s.expression === "thinking" ? 0 : 0;
  const leftUp = s.expression === "thinking" ? 14 : 0;
  const line = (cx: number, side: number, extra: number) => (
    <path d={`M${cx - w / 2},${y - up - extra + side * tilt} Q${cx},${y - up - extra - 8} ${cx + w / 2},${y - up - extra - side * tilt}`}
      stroke={colour} strokeWidth={9} strokeLinecap="round" fill="none" />
  );
  return <g>{line(lx, 1, leftUp)}{line(rx, -1, 0)}</g>;
};

const shade = (hex: string, amount: number) => {
  const n = parseInt(hex.replace("#", ""), 16);
  const f = (c: number) => Math.max(0, Math.min(255, Math.round(c * (1 + amount))));
  return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`;
};

// ---- the characters (drawn in a 400 x 600 box) ---------------------------------------------------------------------

const Lola: React.FC<{ s: FaceState; colour?: string | null }> = ({ s, colour }) => {
  const c = colour || "#FF9E7A";
  return (
    <g>
      <rect x={95} y={360} width={210} height={260} rx={90} fill="#5B7CFA" />
      <circle cx={200} cy={225} r={155} fill={c} />
      <circle cx={160} cy={78} r={30} fill={shade(c, -0.18)} />
      <circle cx={200} cy={66} r={34} fill={shade(c, -0.18)} />
      <circle cx={240} cy={78} r={30} fill={shade(c, -0.18)} />
      <circle cx={112} cy={268} r={22} fill="#FF6F91" opacity={0.35} />
      <circle cx={288} cy={268} r={22} fill="#FF6F91" opacity={0.35} />
      <Brows lx={145} rx={255} y={150} w={56} s={s} />
      <Eye x={145} y={205} rx={32} ry={38} s={s} lid={c} />
      <Eye x={255} y={205} rx={32} ry={38} s={s} lid={c} />
      <Mouth shape={s.shape} expression={s.expression} x={200} y={300} />
    </g>
  );
};

const Max: React.FC<{ s: FaceState; colour?: string | null }> = ({ s, colour }) => {
  const c = colour || "#7FD1AE";
  return (
    <g>
      <rect x={100} y={380} width={200} height={240} rx={80} fill="#F6B93B" />
      <ellipse cx={58} cy={235} rx={30} ry={42} fill={shade(c, -0.12)} />
      <ellipse cx={342} cy={235} rx={30} ry={42} fill={shade(c, -0.12)} />
      <ellipse cx={200} cy={225} rx={142} ry={170} fill={c} />
      <path d="M120,70 Q200,20 280,70 Q200,52 120,70 Z" fill={shade(c, -0.3)} />
      <Brows lx={148} rx={252} y={140} w={52} s={s} colour={shade(c, -0.55)} />
      <Eye x={148} y={200} rx={28} ry={32} s={s} lid={c} />
      <Eye x={252} y={200} rx={28} ry={32} s={s} lid={c} />
      <circle cx={148} cy={200} r={46} fill="none" stroke={INK} strokeWidth={6} />
      <circle cx={252} cy={200} r={46} fill="none" stroke={INK} strokeWidth={6} />
      <path d="M194,200 L206,200" stroke={INK} strokeWidth={6} />
      <Mouth shape={s.shape} expression={s.expression} x={200} y={305} />
    </g>
  );
};

const Pixel: React.FC<{ s: FaceState; colour?: string | null }> = ({ s, colour }) => {
  const c = colour || "#B9C6DA";
  const glow = 0.35 + 0.65 * s.talk;
  const screen = "#1B2433";
  const lightBlue = "#5CE1FF";
  const eye = (x: number) => {
    const h = 44 * (1 - s.blink) + 4;
    const grow = s.expression === "surprised" ? 1.2 : 1;
    return <rect x={x - 17 * grow + s.lookX * 10} y={200 - h / 2 + s.lookY * 8} width={34 * grow} height={h} rx={12} fill={lightBlue} />;
  };
  return (
    <g>
      <line x1={200} y1={95} x2={200} y2={40} stroke={shade(c, -0.35)} strokeWidth={8} />
      <circle cx={200} cy={34} r={16} fill={lightBlue} opacity={glow} />
      <rect x={120} y={390} width={160} height={220} rx={50} fill={shade(c, -0.15)} />
      <circle cx={200} cy={470} r={22} fill={lightBlue} opacity={glow} />
      <rect x={55} y={95} width={290} height={290} rx={70} fill={c} />
      <rect x={85} y={130} width={230} height={215} rx={50} fill={screen} />
      {eye(160)}
      {eye(240)}
      {s.expression === "happy" ? (
        <g><path d="M140,165 Q160,152 180,165" stroke={lightBlue} strokeWidth={6} fill="none" />
          <path d="M220,165 Q240,152 260,165" stroke={lightBlue} strokeWidth={6} fill="none" /></g>
      ) : null}
      <Mouth shape={s.shape} expression={s.expression} x={200} y={290} ink={lightBlue} inside="#0E5A6E" />
    </g>
  );
};

const LOOK_COMPONENTS: Record<Look, React.FC<{ s: FaceState; colour?: string | null }>> = { lola: Lola, max: Max, pixel: Pixel };

// ---- timing ----------------------------------------------------------------------------------------------------------

const hash = (n: number) => {
  const x = Math.sin(n * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};

// Blinks every 3 to 5 s, at different moments for each character.
const blinkAt = (t: number, seed: number) => {
  let at = 0.8 + hash(seed + 1) * 2;
  for (let i = 0; i < 400 && at < t + 1; i++) {
    const d = Math.abs(t - at);
    if (d < 0.09) return 1 - d / 0.09;
    at += 3 + hash(seed * 31 + i) * 2;
  }
  return 0;
};

const shapeAt = (turn: PuppetTurn | undefined, t: number): Shape => {
  if (!turn) return "X";
  let shape: Shape = "X";
  for (const [at, s] of turn.mouth) {
    if (at <= t) shape = s;
    else break;
  }
  return shape;
};

const OPEN: Record<Shape, number> = { X: 0, A: 0, B: 0.3, C: 0.6, D: 1, E: 0.7, F: 0.4, G: 0.3, H: 0.6 };

// ---- the scene -------------------------------------------------------------------------------------------------------

export const Puppet: React.FC<PuppetProps> = (input) => {
  const p = { ...defaults, ...input };
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const t = frame / fps;
  const vertical = H > W;
  const n = Math.min(p.characters.length, 2);
  const speaking = p.turns.find((u) => u.start <= t && t < u.end);
  const current = [...p.turns].reverse().find((u) => u.start <= t + 0.05) ?? p.turns[0];

  const size = vertical ? (n === 1 ? 980 : 660) : n === 1 ? 860 : 760; // height of a character in pixels
  const baseY = vertical ? H * 0.72 : H * 0.98; // where the bottom of the character sits: above the captions
  const xs = n === 1 ? [W / 2] : vertical ? [W * 0.27, W * 0.73] : [W * 0.3, W * 0.7]; // never overlapping

  return (
    <AbsoluteFill style={{ background: `linear-gradient(${p.bgTop}, ${p.bgBottom})`, overflow: "hidden" }}>
      {p.background ? <Img src={staticFile(p.background)} style={{ position: "absolute", width: W, height: H, objectFit: "cover" }} /> : null}
      {!p.background ? (
        <div style={{ position: "absolute", left: -W * 0.2, right: -W * 0.2, top: baseY - size * 0.06, height: H, background: p.floor,
          borderRadius: `50% 50% 0 0 / ${size * 0.12}px ${size * 0.12}px 0 0` }} />
      ) : null}
      {p.characters.slice(0, 2).map((c, i) => {
        const mine = speaking && speaking.speaker === c.name ? speaking : undefined;
        const other = speaking && speaking.speaker !== c.name;
        const lastOwn = [...p.turns].reverse().find((u) => u.speaker === c.name && u.start <= t + 0.05)
          ?? p.turns.find((u) => u.speaker === c.name);
        const shape = shapeAt(mine, t);
        const myTurns = p.turns.filter((u) => u.speaker === c.name);
        const lean = Math.max(0, ...myTurns.map((u) => interpolate(t, [u.start - 0.2, u.start, u.end, u.end + 0.25], [0, 1, 1, 0], clamp)));
        const towards = n === 1 ? 0 : i === 0 ? 1 : -1; // the other character's side
        const s: FaceState = {
          shape,
          blink: blinkAt(t, i * 7 + 3),
          lookX: other ? towards : (lastOwn?.expression === "thinking" ? -0.6 : 0),
          lookY: lastOwn?.expression === "thinking" && !mine ? -0.8 : 0,
          expression: (lastOwn?.expression ?? "neutral") as Expression,
          talk: mine ? Math.max(0.3, OPEN[shape]) : 0,
        };
        const breathe = Math.sin((t * 2 * Math.PI) / 3.2 + i * 1.7) * 6;
        const bob = -OPEN[shape] * 6;
        const scale = (size / 600) * (1 + 0.035 * lean);
        const rotate = towards * 2.5 * lean;
        const Character = LOOK_COMPONENTS[c.look] ?? Lola;
        return (
          <svg key={c.name} width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
            <g transform={`translate(${xs[i]},${baseY + breathe + bob}) rotate(${rotate}) scale(${scale}) translate(-200,-600)`}>
              <Character s={s} colour={c.colour} />
            </g>
          </svg>
        );
      })}
      {p.showTranslation && current?.translation ? (
        <div style={{ position: "absolute", left: 60, right: 60, bottom: vertical ? 150 : 40, textAlign: "center",
          fontFamily: p.font, fontStyle: "italic", fontWeight: 600, fontSize: vertical ? 46 : 38, color: p.translationColor,
          opacity: interpolate(t, [current.start - 0.15, current.start, current.end + 0.3, current.end + 0.5], [0, 1, 1, 0], clamp) }}>
          {current.translation}
        </div>
      ) : null}
      {p.audio ? <Audio src={staticFile(p.audio)} /> : null}
    </AbsoluteFill>
  );
};

export const PuppetComposition: React.FC = () => (
  <Composition
    id="Puppet"
    component={Puppet}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
    // Only the required props, empty: Remotion merges these into every render, so sample turns would leak.
    defaultProps={{ characters: [], turns: [] } as PuppetProps}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      const last = p.turns.length ? p.turns[p.turns.length - 1].end + 0.8 : 3;
      return { durationInFrames: Math.max(1, Math.round((p.length ?? last) * p.fps)), fps: p.fps, width: p.width, height: p.height };
    }}
  />
);
