// Puppet video: one or two characters, drawn here in code, saying the turns of a dialogue with the right mouth shape
// for each sound, blinking, breathing, leaning in when they talk and looking at whoever speaks.
// The props come from scripts/dialogue.py (puppet-props.json): characters, turns with times, mouth shapes and
// expressions, and the length. Copy voice.wav into the Remotion project's public folder and add "audio": "voice.wav".
//
// Characters (look), adults in a flat editorial style, seen from the chest up behind a table: "lola" (a woman with
// shoulder-length hair), "max" (a man with a beard and glasses) and "pixel" (a sleek robot for AI topics). "colour"
// is the clothes colour (the robot's body), "skin" and "hair" change a person's skin tone and hair colour. Every character is one component with the same props
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
  characters: { name: string; look: Look; colour?: string | null; skin?: string | null; hair?: string | null }[];
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
  bgTop: "#F2EDE6",
  bgBottom: "#DCD3C8",
  floor: "#E9E2D8",
  showTranslation: false,
  translationColor: "#2B2622",
  font: "sans-serif",
  fps: 30,
  width: 1080,
  height: 1920,
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const INK = "#2A2320";

// ---- the face parts, shared by every character ---------------------------------------------------------------------

type FaceState = { shape: Shape; blink: number; lookX: number; lookY: number; expression: Expression; talk: number };
type CharacterProps = { s: FaceState; colour?: string | null; skin?: string | null; hair?: string | null };

// The nine mouth shapes, drawn at 1:1 around (x, y); `size` scales them (adult faces use a smaller mouth).
const Mouth: React.FC<{ shape: Shape; expression: Expression; x: number; y: number; size?: number; ink?: string; inside?: string }> = ({
  shape, expression, x, y, size = 1, ink = INK, inside = "#5A1E2E" }) => {
  const teeth = "#FBF8F3";
  const tongue = "#D9727C";
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
      body = (<g><ellipse cx={0} cy={6} rx={30} ry={22} fill={inside} />
        <ellipse cx={0} cy={18} rx={17} ry={8} fill={tongue} />
        <rect x={-21} y={-15} width={42} height={7} rx={3} fill={teeth} /></g>);
      break;
    case "E": // o: rounded
      body = <ellipse cx={0} cy={4} rx={18} ry={18} fill={inside} stroke={ink} strokeWidth={4} />;
      break;
    case "F": // oo, w: puckered
      body = <ellipse cx={0} cy={2} rx={10} ry={12} fill={inside} stroke={ink} strokeWidth={6} />;
      break;
    case "G": // f, v: upper teeth on the lower lip
      body = (<g><ellipse cx={0} cy={2} rx={24} ry={10} fill={inside} />
        <rect x={-18} y={-6} width={36} height={10} rx={3} fill={teeth} /></g>);
      break;
    case "H": // l: open, tongue up
      body = (<g><ellipse cx={0} cy={4} rx={26} ry={17} fill={inside} />
        <ellipse cx={0} cy={-4} rx={12} ry={7} fill={tongue} /></g>);
      break;
    default: { // X: at rest, shaped by the expression
      const curve = expression === "happy" ? 12 : expression === "sad" ? -8 : expression === "surprised" ? 0 : 3;
      body = expression === "surprised"
        ? <ellipse cx={0} cy={2} rx={10} ry={12} fill={inside} stroke={ink} strokeWidth={4} />
        : <path d={`M-26,0 Q0,${curve} 26,0`} stroke={ink} strokeWidth={7} fill="none" strokeLinecap="round" />;
    }
  }
  return <g transform={`translate(${x},${y}) scale(${size})`}>{body}</g>;
};

// An adult eye: an almond with an iris that looks around, an upper lid line, and a lid that closes in the skin colour.
const Eye: React.FC<{ x: number; y: number; s: FaceState; skin: string; iris?: string; mirror?: boolean }> = ({
  x, y, s, skin, iris = "#3B2A22", mirror = false }) => {
  const id = "eye" + React.useId().replace(/[^a-zA-Z0-9]/g, "");
  const w = 17;
  const h = s.expression === "surprised" ? 13 : s.expression === "happy" ? 8 : 10;
  const almond = `M${-w},0 Q${-w * 0.35},${-h * 1.25} ${w * 0.25},${-h} Q${w * 0.8},${-h * 0.75} ${w},0 Q${w * 0.2},${h} ${-w},0 Z`;
  const ix = s.lookX * 6;
  const iy = s.lookY * 3;
  return (
    <g transform={`translate(${x},${y}) scale(${mirror ? -1 : 1},1)`}>
      <clipPath id={id}><path d={almond} /></clipPath>
      <path d={almond} fill="#FAF7F2" />
      <g clipPath={`url(#${id})`}>
        <circle cx={mirror ? -ix : ix} cy={iy} r={8} fill={iris} />
        <circle cx={mirror ? -ix : ix} cy={iy} r={3.6} fill="#15100E" />
        <circle cx={(mirror ? -ix : ix) + 2.5} cy={iy - 2.8} r={1.8} fill="#FFFFFF" />
        <rect x={-w - 2} y={-h * 1.3} width={w * 2 + 4} height={h * 2.6 * s.blink} fill={skin} />
      </g>
      <path d={`M${-w - 2},1 Q${-w * 0.35},${-h * 1.3} ${w * 0.25},${-h - 1} Q${w * 0.8},${-h * 0.8} ${w + 2},0`}
        stroke={INK} strokeWidth={3.2} fill="none" strokeLinecap="round" />
    </g>
  );
};

// Brows: thin and in the hair colour; they carry most of an adult face's expression.
const Brows: React.FC<{ lx: number; rx: number; y: number; s: FaceState; colour: string }> = ({ lx, rx, y, s, colour }) => {
  const up = s.expression === "surprised" ? 9 : s.expression === "happy" ? 3 : 0;
  const inner = s.expression === "sad" ? 6 : s.expression === "thinking" ? -3 : 0; // inner ends up when sad, down when thinking
  const brow = (cx: number, side: number, extra: number) => {
    const a = cx - side * 20; // inner end
    const b = cx + side * 18; // outer end
    return <path d={`M${a},${y - up - extra - inner} Q${cx},${y - up - extra - 7} ${b},${y - up - extra + 2}`}
      stroke={colour} strokeWidth={6} strokeLinecap="round" fill="none" />;
  };
  return <g>{brow(lx, 1, s.expression === "thinking" ? 6 : 0)}{brow(rx, -1, 0)}</g>;
};

const shade = (hex: string, amount: number) => {
  const n = parseInt(hex.replace("#", ""), 16);
  const f = (c: number) => Math.max(0, Math.min(255, Math.round(c * (1 + amount))));
  return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`;
};

// The parts every person shares: shoulders in the clothes colour, neck, ears, the face shape, nose, eyes and mouth.
// Hair is drawn by each character, behind (`back`) and in front (`front`) of the face.
const Person: React.FC<CharacterProps & { clothes: string; skinTone: string; hairColour: string; back?: React.ReactNode;
  front?: React.ReactNode; neckline?: React.ReactNode; extra?: React.ReactNode; lips: string }> = ({
  s, clothes, skinTone, hairColour, back, front, neckline, extra, lips }) => (
  <g>
    {back}
    <path d="M30,600 L30,505 C30,445 85,412 150,404 L250,404 C315,412 370,445 370,505 L370,600 Z" fill={clothes} />
    <rect x={170} y={318} width={60} height={92} rx={14} fill={shade(skinTone, -0.14)} />
    {neckline}
    <ellipse cx={110} cy={244} rx={13} ry={22} fill={shade(skinTone, -0.06)} />
    <ellipse cx={290} cy={244} rx={13} ry={22} fill={shade(skinTone, -0.06)} />
    <path d="M110,222 C110,150 150,124 200,124 C250,124 290,150 290,222 C290,292 258,346 200,350 C142,346 110,292 110,222 Z" fill={skinTone} />
    <Brows lx={166} rx={234} y={208} s={s} colour={shade(hairColour, 0.05)} />
    <Eye x={166} y={232} s={s} skin={skinTone} />
    <Eye x={234} y={232} s={s} skin={skinTone} mirror />
    <path d="M203,240 Q194,268 199,276 Q205,280 213,274" stroke={shade(skinTone, -0.32)} strokeWidth={3.5} fill="none" strokeLinecap="round" />
    <Mouth shape={s.shape} expression={s.expression} x={200} y={307} size={0.62} ink={lips} inside="#4A1E22" />
    {front}
    {extra}
  </g>
);

// ---- the characters (drawn in a 400 x 600 box, cut at the chest) -----------------------------------------------------

// Lola: a woman with shoulder-length hair and a side fringe, small gold earrings.
const Lola: React.FC<CharacterProps> = ({ s, colour, skin, hair }) => {
  const skinTone = skin || "#F2CDB0";
  const h = hair || "#3A2722";
  return (
    <Person s={s} clothes={colour || "#B9553F"} skinTone={skinTone} hairColour={h} lips={shade(skinTone, -0.38)}
      back={<path d="M98,232 C88,128 140,100 200,100 C262,100 314,128 304,232 C302,300 306,350 316,396 Q290,410 258,402
        C272,350 280,300 280,250 L120,250 C120,300 128,350 142,402 Q110,410 84,396 C94,350 98,300 98,232 Z" fill={h} />}
      neckline={<path d="M168,404 Q200,452 232,404 Z" fill={shade(skinTone, -0.14)} />}
      front={<path d="M110,222 C108,148 158,112 214,114 C268,116 296,150 292,214 C276,176 244,156 204,158
        C168,160 132,184 110,222 Z" fill={h} />}
      extra={<g><circle cx={110} cy={272} r={5} fill="#D9B45A" /><circle cx={290} cy={272} r={5} fill="#D9B45A" /></g>} />
  );
};

// Max: a man with short hair, a trimmed beard, thin glasses and a shirt collar.
const Max: React.FC<CharacterProps> = ({ s, colour, skin, hair }) => {
  const skinTone = skin || "#F5D6BF";
  const h = hair || "#9A7550";
  return (
    <Person s={s} clothes={colour || "#2F5D62"} skinTone={skinTone} hairColour={h} lips={shade(skinTone, -0.42)}
      neckline={<g><path d="M166,404 L200,440 L182,456 L150,414 Z" fill="#F2EEE8" />
        <path d="M234,404 L200,440 L218,456 L250,414 Z" fill="#F2EEE8" /></g>}
      front={<g>
        <path d="M108,218 C102,132 152,110 206,110 C262,110 300,136 292,218 C284,178 268,160 246,156
          C206,150 160,156 132,168 C118,180 111,198 108,218 Z" fill={h} />
        <path d="M112,262 C118,322 160,352 200,354 C240,352 282,322 288,262 C276,296 252,316 232,318 Q200,290 168,318
          C148,316 124,296 112,262 Z" fill={h} opacity={0.85} />
        <rect x={140} y={214} width={52} height={36} rx={11} fill="none" stroke={INK} strokeWidth={3.5} />
        <rect x={208} y={214} width={52} height={36} rx={11} fill="none" stroke={INK} strokeWidth={3.5} />
        <path d="M192,228 Q200,222 208,228" stroke={INK} strokeWidth={3.5} fill="none" />
      </g>} />
  );
};

// Pixel: a sleek assistant robot for AI topics, with a dark visor; its lights glow while it talks.
const Pixel: React.FC<CharacterProps> = ({ s, colour }) => {
  const c = colour || "#C9D0DA";
  const glow = 0.45 + 0.55 * s.talk;
  const visor = "#141A24";
  const light = "#7FE3F0";
  const eye = (x: number) => {
    const h = 30 * (1 - s.blink) + 4;
    const grow = s.expression === "surprised" ? 1.2 : 1;
    return <rect x={x - 11 * grow + s.lookX * 9} y={222 - h / 2 + s.lookY * 7} width={22 * grow} height={h} rx={11} fill={light} />;
  };
  return (
    <g>
      <path d="M40,600 L40,510 C40,450 95,418 160,410 L240,410 C305,418 360,450 360,510 L360,600 Z" fill={shade(c, -0.18)} />
      <rect x={176} y={330} width={48} height={90} rx={10} fill={shade(c, -0.35)} />
      <circle cx={200} cy={490} r={12} fill={light} opacity={glow} />
      <line x1={200} y1={128} x2={200} y2={92} stroke={shade(c, -0.35)} strokeWidth={6} />
      <circle cx={200} cy={88} r={8} fill={light} opacity={glow} />
      <ellipse cx={86} cy={234} rx={16} ry={34} fill={shade(c, -0.25)} />
      <ellipse cx={314} cy={234} rx={16} ry={34} fill={shade(c, -0.25)} />
      <rect x={90} y={126} width={220} height={216} rx={64} fill={c} />
      <rect x={110} y={168} width={180} height={140} rx={44} fill={visor} />
      {eye(166)}
      {eye(234)}
      {s.expression === "happy" ? (
        <g><path d="M152,198 Q166,190 180,198" stroke={light} strokeWidth={5} fill="none" strokeLinecap="round" />
          <path d="M220,198 Q234,190 248,198" stroke={light} strokeWidth={5} fill="none" strokeLinecap="round" /></g>
      ) : null}
      <Mouth shape={s.shape} expression={s.expression} x={200} y={276} size={0.7} ink={light} inside={light} />
    </g>
  );
};

const LOOK_COMPONENTS: Record<Look, React.FC<CharacterProps>> = { lola: Lola, max: Max, pixel: Pixel };

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

  const size = vertical ? (n === 1 ? 1100 : 800) : n === 1 ? 900 : 820; // height of a character in pixels
  const baseY = vertical ? H * 0.72 : H * 0.98; // where the bottom of the character sits: above the captions
  const tableY = baseY - size * 0.1;
  const xs = n === 1 ? [W / 2] : vertical ? [W * 0.27, W * 0.73] : [W * 0.3, W * 0.7]; // never overlapping

  return (
    <AbsoluteFill style={{ background: `linear-gradient(${p.bgTop}, ${p.bgBottom})`, overflow: "hidden" }}>
      {p.background ? <Img src={staticFile(p.background)} style={{ position: "absolute", width: W, height: H, objectFit: "cover" }} /> : null}
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
        const breathe = Math.sin((t * 2 * Math.PI) / 3.6 + i * 1.7) * 3;
        const bob = -OPEN[shape] * 2;
        const scale = (size / 600) * (1 + 0.02 * lean);
        const rotate = towards * 1.5 * lean;
        const Character = LOOK_COMPONENTS[c.look] ?? Lola;
        return (
          <svg key={c.name} width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
            <g transform={`translate(${xs[i]},${baseY + breathe + bob}) rotate(${rotate}) scale(${scale}) translate(-200,-600)`}>
              <Character s={s} colour={c.colour} skin={c.skin} hair={c.hair} />
            </g>
          </svg>
        );
      })}
      {!p.background ? ( // a table in front, so the characters (cut at the chest) sit behind it
        <div style={{ position: "absolute", left: 0, right: 0, top: tableY, height: H - tableY, background: p.floor,
          borderTop: `${Math.round(size * 0.012)}px solid rgba(255,255,255,0.55)`, boxShadow: "0 -6px 18px rgba(0,0,0,0.08)" }} />
      ) : null}
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
