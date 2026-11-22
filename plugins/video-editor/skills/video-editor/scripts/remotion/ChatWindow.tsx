// An AI chat window for videos about AI: the prompt types into the box with a blinking caret, the send button
// pulses, the prompt becomes a bubble, three dots "think", and the answer appears word by word (lines starting with
// "- " show as a list). Every time comes from scripts/chatwindow.py, which reads chat.json and the captions, so this
// file only draws: never edit it for one video.
// It is a clean, generic chat design in the brand's colours with the app's name (and its press-kit logo, if given),
// not a copy of any company's real interface.
// background "transparent" lays the window over the speaker (render as ProRes 4444); any colour makes a full-screen part.
//
// Copy this file and brandFont.ts into the Remotion project's src folder, then register it in src/Root.tsx:
//   import { ChatWindowComposition } from "./ChatWindow";
//   ... <ChatWindowComposition />
// Render one (props from chatwindow.py, in a file so accents and emoji survive on Windows):
//   npx remotion render src/index.ts ChatWindow out/chat.mov --props=chat-props.json
import React from "react";
import { AbsoluteFill, Composition, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrandFont } from "./brandFont";

export type ChatMessage =
  | { role: "user"; text: string; typeFrom: number; typeTo: number; sent: number }
  | { role: "assistant"; text: string; from: number; answer: number; framesPerWord: number };

export type ChatWindowProps = {
  messages: ChatMessage[];
  app?: string;
  logo?: string; // inside public/, from the brand's press kit
  placeholder?: string;
  theme?: "light" | "dark";
  fontSize?: number;
  font?: string;
  fontFile?: string;
  accentColor?: string;
  background?: string; // "transparent" to lay it over the speaker
  background2?: string;
  seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
};

const defaults = {
  app: "Assistant",
  logo: "",
  placeholder: "Escribe un mensaje…",
  theme: "light" as "light" | "dark",
  fontSize: 36,
  font: "sans-serif",
  fontFile: "",
  accentColor: "#FF4F8B",
  background: "#1B1033",
  background2: "#0E2A47",
  seconds: 8,
  fps: 30,
  width: 1920,
  height: 1080,
};

const THEMES = {
  light: { window: "#FFFFFF", text: "#1A1A1A", soft: "#6B6B76", bar: "#F4F4F7", input: "#F1F1F5", line: "#E4E4EA" },
  dark: { window: "#1E1E24", text: "#F2F2F5", soft: "#9A9AA6", bar: "#26262E", input: "#2C2C35", line: "#34343E" },
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// The first `count` words of a text, keeping its lines; lines starting with "- " become list items.
const AnswerText: React.FC<{ text: string; count: number; accent: string; size: number }> = ({ text, count, accent, size }) => {
  let left = count;
  const lines = text.split("\n");
  return (
    <div>
      {lines.map((line, i) => {
        if (left <= 0) return null;
        const bullet = line.trim().startsWith("- ");
        const words = (bullet ? line.trim().slice(2) : line).split(/\s+/).filter(Boolean);
        const shown = words.slice(0, left);
        left -= words.length;
        return (
          <div key={i} style={{ display: "flex", gap: size * 0.4, marginTop: i ? size * 0.25 : 0 }}>
            {bullet ? <span style={{ color: accent, fontWeight: 800 }}>•</span> : null}
            <span>{shown.join(" ")}</span>
          </div>
        );
      })}
    </div>
  );
};

const Avatar: React.FC<{ logo: string; app: string; accent: string; size: number }> = ({ logo, app, accent, size }) =>
  logo ? (
    <Img src={staticFile(logo)} style={{ width: size, height: size, borderRadius: size / 2, objectFit: "cover", flexShrink: 0 }} />
  ) : (
    <div style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: accent, color: "#FFFFFF",
      display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: size * 0.5, flexShrink: 0 }}>
      {app.slice(0, 1).toUpperCase()}
    </div>
  );

export const ChatWindow: React.FC<ChatWindowProps> = (input) => {
  const p = { ...defaults, ...input };
  useBrandFont(p.font, p.fontFile || undefined);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = THEMES[p.theme];
  const s = p.fontSize;
  const vertical = p.height > p.width;
  // Wide: a broad window, so a prompt fits on one line and a short answer doesn't push it out of view.
  const winW = vertical ? p.width * 0.88 : Math.min(p.width * 0.74, s * 30);
  const winH = vertical ? p.height * 0.62 : p.height * 0.88;
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 140 } });
  const leave = interpolate(frame, [durationInFrames - 8, durationInFrames - 1], [1, 0], clamp);
  const overSpeaker = p.background === "transparent";

  const typing = p.messages.find((m) => m.role === "user" && frame >= m.typeFrom && frame < m.sent) as
    | Extract<ChatMessage, { role: "user" }>
    | undefined;
  const typedChars = typing
    ? Math.round(interpolate(frame, [typing.typeFrom, typing.typeTo], [0, typing.text.length], clamp))
    : 0;
  const caretOn = Math.floor(frame / Math.max(1, Math.round(fps * 0.5))) % 2 === 0;
  const justSent = p.messages.some((m) => m.role === "user" && frame >= m.sent && frame < m.sent + 6);

  return (
    <AbsoluteFill style={{ fontFamily: p.font, alignItems: "center", justifyContent: "center",
      background: overSpeaker ? "transparent" : `linear-gradient(135deg, ${p.background} 0%, ${p.background2} 100%)` }}>
      <div
        style={{
          width: winW, height: winH, borderRadius: s * 0.8, backgroundColor: t.window, color: t.text,
          boxShadow: "0 30px 80px rgba(0,0,0,0.35)", display: "flex", flexDirection: "column", overflow: "hidden",
          transform: `scale(${0.92 + 0.08 * enter})`, opacity: Math.min(1, enter * 1.4) * leave, fontSize: s,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: s * 0.5, padding: `${s * 0.55}px ${s * 0.8}px`,
          backgroundColor: t.bar, borderBottom: `2px solid ${t.line}` }}>
          <Avatar logo={p.logo} app={p.app} accent={p.accentColor} size={s * 1.3} />
          <div style={{ fontWeight: 800 }}>{p.app}</div>
          <div style={{ flex: 1 }} />
          {[0, 1, 2].map((i) => (
            <div key={i} style={{ width: s * 0.32, height: s * 0.32, borderRadius: s, backgroundColor: t.line, marginLeft: s * 0.2 }} />
          ))}
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: s * 0.6,
          padding: `${s * 0.8}px ${s * 0.9}px`, overflow: "hidden" }}>
          {p.messages.map((m, i) => {
            if (m.role === "user") {
              if (frame < m.sent) return null;
              const pop = spring({ frame: frame - m.sent, fps, config: { damping: 16, stiffness: 180 } });
              return (
                <div key={i} style={{ alignSelf: "flex-end", maxWidth: "78%", backgroundColor: p.accentColor, color: "#FFFFFF",
                  padding: `${s * 0.45}px ${s * 0.7}px`, borderRadius: s * 0.7, borderBottomRightRadius: s * 0.2,
                  transform: `translateY(${(1 - pop) * s}px)`, opacity: pop, lineHeight: 1.3 }}>
                  {m.text}
                </div>
              );
            }
            if (frame < m.from) return null;
            const thinking = frame < m.answer;
            const words = Math.floor((frame - m.answer) / m.framesPerWord) + 1;
            return (
              <div key={i} style={{ display: "flex", gap: s * 0.5, alignItems: "flex-start", maxWidth: "92%", lineHeight: 1.35 }}>
                <Avatar logo={p.logo} app={p.app} accent={p.accentColor} size={s * 1.1} />
                {thinking ? (
                  <div style={{ display: "flex", gap: s * 0.25, paddingTop: s * 0.35 }}>
                    {[0, 1, 2].map((d) => (
                      <div key={d} style={{ width: s * 0.3, height: s * 0.3, borderRadius: s, backgroundColor: t.soft,
                        opacity: 0.35 + 0.65 * Math.max(0, Math.sin(((frame - m.from) / fps) * 7 - d * 0.9)) }} />
                    ))}
                  </div>
                ) : (
                  <AnswerText text={m.text} count={words} accent={p.accentColor} size={s} />
                )}
              </div>
            );
          })}
        </div>

        <div style={{ padding: `${s * 0.6}px ${s * 0.8}px`, borderTop: `2px solid ${t.line}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: s * 0.5, backgroundColor: t.input,
            borderRadius: s * 0.9, padding: `${s * 0.45}px ${s * 0.5}px ${s * 0.45}px ${s * 0.8}px` }}>
            <div style={{ flex: 1, color: typing ? t.text : t.soft, whiteSpace: "nowrap", overflow: "hidden" }}>
              {typing ? typing.text.slice(0, typedChars) : p.placeholder}
              {typing ? <span style={{ opacity: caretOn ? 1 : 0, color: p.accentColor, fontWeight: 300 }}>|</span> : null}
            </div>
            <div style={{ width: s * 1.4, height: s * 1.4, borderRadius: s, backgroundColor: p.accentColor, color: "#FFFFFF",
              display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800,
              transform: `scale(${justSent ? 0.85 : 1})`, opacity: typing || justSent ? 1 : 0.45 }}>
              ↑
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const ChatWindowComposition: React.FC = () => (
  <Composition
    id="ChatWindow"
    component={ChatWindow}
    durationInFrames={240}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ messages: [] }}
    calculateMetadata={({ props }) => {
      const p = { ...defaults, ...props };
      return { fps: p.fps, width: p.width, height: p.height, durationInFrames: Math.max(1, Math.round(p.seconds * p.fps)) };
    }}
  />
);
