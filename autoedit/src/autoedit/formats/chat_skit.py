"""chat-skit: a script of characters, messages, cards and beats becomes a Discord-style animated
episode (dark chat UI, avatar/name/timestamp rows, big grey text cards, typing indicators, a highlight
band on the newest message). Camera punch-ins on punchlines are EDL zooms anchored to the focus
track, which follows the newest message the way the face track follows a face.

Script (YAML):
    title: "..."
    server: "FrogBert's Server"        # optional
    channel: general                   # optional
    characters:
      frog: {name: FrogBert, avatar: frog.png, color: "#57F287"}
      dan:  {name: Dan, avatar: dan.png}
    scenes:
      - card: "3 AM. The group chat wakes up."      # dur: 2.5
      - msg: {from: dan, text: "who's awake", typing: 1.4, time: "3:02 AM"}
      - msg: {from: frog, text: "I never sleep.", punch: true, hold: 1.0}
      - beat: 1.2
      - sfx: notification
"""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..edl.transcript import Sentence, Transcript, Word
from ..media.faces import FaceBox, FaceTrack
from ..media.text import hex_to_rgb, resolve_font
from ..profile import Profile

W, H = 1920, 1080
FPS = 30
RAIL_W, PANEL_W, HEADER_H, INPUT_H = 72, 240, 56, 76
CHAT_X = RAIL_W + PANEL_W
AVATAR_X = CHAT_X + 28
TEXT_X_OFFSET = 112
TEXT_MAX_W = W - CHAT_X - 180
MSG_GAP = 26
FOCUS_DT = 0.1


@dataclass
class Character:
    key: str
    name: str
    color: str = "#F2F3F5"
    avatar: Path | None = None


@dataclass
class Event:
    kind: str                 # card | msg | beat | sfx
    t0: float
    t1: float
    data: dict[str, Any] = field(default_factory=dict)
    # msg only
    appear: float = 0.0       # when the message pops in (after typing)


@dataclass
class Script:
    title: str
    server: str
    channel: str
    characters: dict[str, Character]
    scenes: list[dict[str, Any]]


def load_script(path: Path, assets_dir: Path | None) -> Script:
    d = yaml.safe_load(path.read_text()) or {}
    chars: dict[str, Character] = {}
    for key, c in (d.get("characters") or {}).items():
        av = None
        if c.get("avatar"):
            p = Path(c["avatar"]).expanduser()
            cands = [p] if p.is_absolute() else [path.parent / p, *(([assets_dir / p]) if assets_dir else [])]
            av = next((x for x in cands if x.exists()), None)
        chars[key] = Character(key, c.get("name", key), c.get("color", "#F2F3F5"), av)
    return Script(d.get("title", path.stem), d.get("server", "FrogBert's Server"), d.get("channel", "general"), chars,
                  list(d.get("scenes") or []))


def reading_time(text: str) -> float:
    words = len(text.split())
    return max(1.3, min(6.0, 0.9 + 0.32 * words))


def schedule(script: Script, profile: Profile) -> tuple[list[Event], float]:
    """Deterministic timeline: cards, typing then message, beats, sfx. Returns events and the duration."""
    t = 0.3
    events: list[Event] = []
    for sc in script.scenes:
        if "card" in sc:
            dur = float(sc.get("dur", profile.cards.duration))
            events.append(Event("card", t, t + dur, {"text": str(sc["card"])}))
            t += dur + 0.25
        elif "msg" in sc:
            m = sc["msg"]
            text = str(m.get("text", ""))
            typing = float(m.get("typing", min(2.4, 0.5 + 0.06 * len(text))))
            read = float(m.get("read", reading_time(text)))
            hold = float(m.get("hold", 0.0))
            appear = t + typing
            ev = Event("msg", t, appear + read + hold, {"from": m.get("from"), "text": text, "punch": bool(m.get("punch")),
                                                        "time": m.get("time"), "typing": typing, "read": read}, appear)
            events.append(ev)
            t = ev.t1
        elif "beat" in sc:
            dur = float(sc["beat"])
            events.append(Event("beat", t, t + dur, {}))
            t += dur
        elif "sfx" in sc:
            events.append(Event("sfx", t, t, {"kind": str(sc["sfx"])}))
    return events, t + 0.5


# ---- drawing --------------------------------------------------------------------------------

class Compositor:
    def __init__(self, script: Script, profile: Profile, font_regular: Path, font_bold: Path):
        self.s = script
        self.c = profile.chat
        self.colors = profile.colors
        self.f_msg = ImageFont.truetype(str(font_regular), self.c.message_size_px)
        self.f_name = ImageFont.truetype(str(font_bold), self.c.name_size_px)
        self.f_time = ImageFont.truetype(str(font_regular), int(self.c.name_size_px * 0.6))
        self.f_card = ImageFont.truetype(str(font_bold), self.c.card_size_px)
        self.f_ui = ImageFont.truetype(str(font_bold), 30)
        self.f_small = ImageFont.truetype(str(font_regular), 26)
        self.avatars: dict[str, Image.Image] = {}
        self.base = self._draw_base()
        self._state_cache: dict[tuple[int, int], tuple[Image.Image, list[tuple[int, int, int, int]]]] = {}

    # static UI
    def _draw_base(self) -> Image.Image:
        im = Image.new("RGB", (W, H), hex_to_rgb(self.c.chat_bg))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, RAIL_W, H], fill=(30, 31, 34))
        for i, col in enumerate([(88, 101, 242), (87, 242, 135), (254, 231, 92), (235, 69, 158)]):
            y = 24 + i * 72
            d.ellipse([12, y, 60, y + 48], fill=col if i else hex_to_rgb(self.c.highlight))
        d.rectangle([4, 24, 8, 72], fill=(255, 255, 255))
        d.rectangle([RAIL_W, 0, CHAT_X, H], fill=hex_to_rgb(self.c.panel_bg))
        d.text((RAIL_W + 18, 14), self.s.server[:22], font=self.f_ui, fill=(255, 255, 255))
        d.line([RAIL_W, 54, CHAT_X, 54], fill=(30, 31, 34), width=2)
        chans = [self.s.channel, "memes", "off-topic", "voice-chat"]
        for i, ch in enumerate(chans):
            y = 84 + i * 44
            if i == 0:
                d.rounded_rectangle([RAIL_W + 10, y - 6, CHAT_X - 10, y + 34], radius=6, fill=(64, 66, 73))
            d.text((RAIL_W + 24, y), f"#  {ch}", font=self.f_small, fill=(255, 255, 255) if i == 0 else hex_to_rgb(self.c.timestamp))
        d.rectangle([CHAT_X, 0, W, HEADER_H], fill=hex_to_rgb(self.c.chat_bg))
        d.line([CHAT_X, HEADER_H, W, HEADER_H], fill=(30, 31, 34), width=2)
        d.text((CHAT_X + 24, 12), f"#  {self.s.channel}", font=self.f_ui, fill=(255, 255, 255))
        # input box
        d.rounded_rectangle([CHAT_X + 24, H - INPUT_H - 24, W - 24, H - 24], radius=12, fill=(56, 58, 64))
        d.text((CHAT_X + 48, H - INPUT_H - 2), f"Message #{self.s.channel}", font=self.f_small, fill=hex_to_rgb(self.c.timestamp))
        return im

    def avatar(self, ch: Character) -> Image.Image:
        if ch.key in self.avatars:
            return self.avatars[ch.key]
        size = self.c.avatar_px
        if ch.avatar and ch.avatar.exists():
            im = Image.open(ch.avatar).convert("RGBA").resize((size, size), Image.LANCZOS)
        else:
            im = Image.new("RGBA", (size, size), hex_to_rgb(ch.color) + (255,))
            d = ImageDraw.Draw(im)
            f = ImageFont.truetype(self.f_name.path, int(size * 0.5))
            d.text((size / 2, size / 2), ch.name[:1].upper(), font=f, fill=(30, 31, 34), anchor="mm")
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        im.putalpha(mask)
        self.avatars[ch.key] = im
        return im

    def wrap(self, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        lines: list[str] = []
        for para in text.split("\n"):
            cur = ""
            for w in para.split(" "):
                cand = (cur + " " + w).strip()
                if font.getlength(cand) <= max_w or not cur:
                    cur = cand
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines

    def message_height(self, text: str) -> int:
        lines = self.wrap(text, self.f_msg, TEXT_MAX_W)
        lh = int(self.c.message_size_px * 1.25)
        return max(self.c.avatar_px, self.c.name_size_px + 10 + lh * len(lines)) + MSG_GAP

    def draw_state(self, msgs: list[dict[str, Any]]) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
        """The chat with these messages visible (newest last), bottom-anchored. Returns the image and each
        message's bounding box (last one = newest)."""
        key = (len(msgs), id(msgs[-1]) if msgs else 0)
        if key in self._state_cache:
            return self._state_cache[key]
        im = self.base.copy()
        d = ImageDraw.Draw(im)
        bottom = H - INPUT_H - 24 - 44
        boxes: list[tuple[int, int, int, int]] = [(0, 0, 0, 0)] * len(msgs)
        y = bottom
        for i in range(len(msgs) - 1, -1, -1):
            m = msgs[i]
            h = self.message_height(m["text"])
            y -= h
            if y < HEADER_H + 10:
                break
            ch = m["char"]
            av = self.avatar(ch)
            im.paste(av, (AVATAR_X, y + 4), av)
            tx = AVATAR_X + TEXT_X_OFFSET
            d.text((tx, y), ch.name, font=self.f_name, fill=hex_to_rgb(ch.color))
            nw = self.f_name.getlength(ch.name)
            d.text((tx + nw + 14, y + int(self.c.name_size_px * 0.35)), m["time"], font=self.f_time, fill=hex_to_rgb(self.c.timestamp))
            lh = int(self.c.message_size_px * 1.25)
            ty = y + self.c.name_size_px + 10
            maxw = 0
            for ln in self.wrap(m["text"], self.f_msg, TEXT_MAX_W):
                d.text((tx, ty), ln, font=self.f_msg, fill=hex_to_rgb(self.c.text))
                maxw = max(maxw, int(self.f_msg.getlength(ln)))
                ty += lh
            boxes[i] = (AVATAR_X - 8, y - 6, TEXT_X_OFFSET + maxw + 24, h - MSG_GAP + 12)
        self._state_cache = {key: (im, boxes)}
        return im, boxes

    def frame(self, t: float, msgs: list[dict[str, Any]], newest_age: float | None, typing: Character | None,
              typing_phase: float, card: tuple[str, float] | None) -> tuple[Image.Image, tuple[int, int, int, int]]:
        """Compose one frame; returns the image and the focus box."""
        im, boxes = self.draw_state(msgs)
        im = im.copy()
        focus = boxes[-1] if boxes else (CHAT_X + 100, H // 2 - 100, 800, 200)
        if msgs and newest_age is not None and newest_age < self.c.highlight_fade_s:
            a = int(90 * (1 - newest_age / self.c.highlight_fade_s))
            x, y, w, h = boxes[-1]
            band = Image.new("RGBA", (W - CHAT_X, h), hex_to_rgb(self.c.highlight) + (a,))
            im.paste(band, (CHAT_X, y), band)
            d = ImageDraw.Draw(im)
            d.rectangle([CHAT_X, y, CHAT_X + 5, y + h], fill=hex_to_rgb(self.c.highlight))
        if typing is not None:
            d = ImageDraw.Draw(im)
            ty = H - INPUT_H - 24 - 36
            label = f"{typing.name} is typing"
            d.text((CHAT_X + 48, ty), label, font=self.f_small, fill=hex_to_rgb(self.c.text))
            lx = CHAT_X + 48 + int(self.f_small.getlength(label)) + 14
            for k in range(3):
                phase = (typing_phase * 3 - k) % 3
                r = 5 + 3 * max(0.0, 1 - abs(phase - 1))
                d.ellipse([lx + k * 22 - r, ty + 16 - r, lx + k * 22 + r, ty + 16 + r], fill=hex_to_rgb(self.c.text))
        if card is not None:
            text, alpha = card
            ov = Image.new("RGBA", (W, H), hex_to_rgb(self.c.card_bg) + (int(255 * alpha),))
            d = ImageDraw.Draw(ov)
            lines = self.wrap(text, self.f_card, int(W * 0.78))
            lh = int(self.c.card_size_px * 1.2)
            y0 = H // 2 - lh * len(lines) // 2
            tw = 0
            for i, ln in enumerate(lines):
                d.text((W // 2, y0 + i * lh + lh // 2), ln, font=self.f_card, fill=hex_to_rgb(self.c.card_text) + (int(255 * alpha),), anchor="mm")
                tw = max(tw, int(self.f_card.getlength(ln)))
            im.paste(ov, (0, 0), ov)
            if alpha > 0.5:
                focus = (W // 2 - tw // 2 - 20, y0 - 10, tw + 40, lh * len(lines) + 20)
        return im, focus


# ---- the format ------------------------------------------------------------------------------

class ChatSkit:
    name = "chat-skit"
    dead_air = False
    captions = False
    planner_notes = ("A scripted chat episode rendered as a Discord-style screen: every pause is deliberate, the "
                     "words are already on screen (no captions), and 'the face' is the newest message. Decide the "
                     "punchlines (dropouts and punch-in zooms), music moods per scene, risers before reveals, and "
                     "whether any scene drags. Sentences read 'Name: message'. Cards are already in the picture.")

    def _script_path(self, project) -> Path:
        s = project.options.get("script")
        if not s:
            raise FileNotFoundError("chat-skit project has no script (create it with --script episode.yaml)")
        return Path(s)

    def compose(self, project, settings, profile: Profile, log) -> Path:
        script = load_script(self._script_path(project), profile.resolve_path(profile.chat.assets_dir))
        events, duration = schedule(script, profile)
        font_b = resolve_font(profile.fonts.primary)
        font_r = resolve_font(profile.fonts.secondary, fallback=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        comp = Compositor(script, profile, font_r.path, font_b.path)
        out = project.ingest_source
        out.parent.mkdir(parents=True, exist_ok=True)
        n_frames = int(duration * FPS)
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "libx264", "-preset", settings.render.preset,
               "-crf", str(settings.render.crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        assert proc.stdin is not None
        msgs_all = [e for e in events if e.kind == "msg"]
        cards = [e for e in events if e.kind == "card"]
        focus: list[FaceBox] = []
        next_focus_t = 0.0
        words: list[Word] = []
        sentences: list[Sentence] = []
        extras: dict[str, Any] = {"sfx": [], "zooms": [], "music_mood": "playful", "scenes": []}
        auto_minute = 2
        for i, e in enumerate(msgs_all):
            ch = script.characters.get(e.data["from"]) or Character(str(e.data["from"]), str(e.data["from"]))
            e.data["char"] = ch
            e.data["time"] = f"Today at 3:{auto_minute:02d} AM" if not e.data.get("time") else f"Today at {e.data['time']}"
            auto_minute += 1
            # transcript: one sentence per message, words spread over the reading time
            toks = e.data["text"].split() or ["..."]
            t0, t1 = e.appear, e.appear + e.data["read"] * 0.85
            w0 = len(words)
            for k, tok in enumerate(toks):
                a = t0 + (t1 - t0) * k / len(toks)
                b = t0 + (t1 - t0) * (k + 1) / len(toks)
                words.append(Word(id=len(words), text=tok, t0=round(a, 3), t1=round(b - 0.02, 3), p=1.0, s=len(sentences)))
            sentences.append(Sentence(id=len(sentences), t0=round(t0, 3), t1=round(t1, 3), text=f"{ch.name}: {e.data['text']}",
                                      w0=w0, w1=len(words) - 1))
            extras["sfx"].append({"kind": "pop", "src": round(e.appear, 3), "reason": f"message from {ch.name} appears"})
            for k in range(int(e.data["typing"] / 0.5)):
                extras["sfx"].append({"kind": "click", "src": round(e.t0 + 0.2 + k * 0.5, 3), "gain_db": -8, "reason": "typing"})
            if e.data["punch"]:
                extras["zooms"].append({"src_in": round(e.appear, 3), "src_out": round(e.appear + e.data["read"], 3),
                                        "scale": profile.chat.punch_scale, "reason": f"punch-in on {ch.name}'s line"})
            extras["scenes"].append({"sentence": len(sentences) - 1, "t0": round(e.t0, 3), "appear": round(e.appear, 3), "t1": round(e.t1, 3)})
        for c in cards:
            extras["sfx"].append({"kind": "whoosh", "src": round(c.t0, 3), "reason": "card slides in"})
        for e in events:
            if e.kind == "sfx":
                extras["sfx"].append({"kind": e.data["kind"], "src": round(e.t0, 3), "reason": "scripted sfx"})
        for fi in range(n_frames):
            t = fi / FPS
            visible = [m.data for m in msgs_all if m.appear <= t]
            newest_age = (t - max(m.appear for m in msgs_all if m.appear <= t)) if visible else None
            typing = None
            phase = 0.0
            for m in msgs_all:
                if m.t0 <= t < m.appear:
                    typing = m.data["char"]
                    phase = (t - m.t0) / profile.chat.typing_dots_s
                    break
            card = None
            for c in cards:
                if c.t0 <= t < c.t1:
                    fade = 0.25
                    a = min(1.0, (t - c.t0) / fade, (c.t1 - t) / fade)
                    card = (c.data["text"], max(0.0, a))
                    break
            im, fb = comp.frame(t, visible, newest_age, typing, phase, card)
            proc.stdin.write(im.tobytes())
            if t >= next_focus_t:
                focus.append(FaceBox(round(t, 3), *map(float, fb), 1.0))
                next_focus_t += FOCUS_DT
            if fi % 150 == 0:
                log.progress(fi / n_frames, f"frame {fi}/{n_frames}")
        proc.stdin.close()
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg failed composing the chat episode")
        d = project.dir("ingest")
        tr = Transcript(language="en", model="script", source_duration=duration, words=words, sentences=sentences,
                        notes=["derived from the chat-skit script: one sentence per message"])
        tr.save(d / "script_transcript.json")
        FaceTrack(W, H, FOCUS_DT, focus, detector="chat-skit focus (newest message)").save(d / "focus_track.json")
        (d / "format_extras.json").write_text(json.dumps(extras, indent=1))
        (d / "schedule.json").write_text(json.dumps([{"kind": e.kind, "t0": e.t0, "t1": e.t1, "appear": e.appear,
                                                       "text": e.data.get("text")} for e in events], indent=1))
        log.info("composed", frames=n_frames, duration=round(duration, 2), messages=len(msgs_all), cards=len(cards))
        return out

    def transcript_file(self, project) -> Path | None:
        p = project.dir("ingest") / "script_transcript.json"
        return p if p.exists() else None

    def focus_track_file(self, project) -> Path | None:
        p = project.dir("ingest") / "focus_track.json"
        return p if p.exists() else None

    def extras(self, project) -> dict[str, Any]:
        p = project.dir("ingest") / "format_extras.json"
        return json.loads(p.read_text()) if p.exists() else {}
