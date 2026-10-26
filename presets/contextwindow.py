"""'Context Window' preset: doompop (mexicat) look adapted to an AI losing memory as its context fills.
Overlays: a token meter that fills through the song, old sung lines scrolling up and fading out the top,
falling token 'snow' in pre-choruses, a context-window frame truncating from the top in choruses,
'> new chat' terminal prompts in the bridge, 'hello world' terminal in intro/outro, a P(doom) meter.
Word events: 'tokens' -> token chips burst, 'new' (new chat) -> prompt spawns, 'hello' -> terminal line,
'window' -> frame pulse, 'remember' -> memory indicator. Photosensitive-safe: no flashes/inversions,
all colour changes are slow continuous ramps, orange only on small elements."""
import math, random
from PIL import Image, ImageDraw
from presets.doompop import Preset as Doom, INK, INK2, GRAPH, ASH, BONE, SIGNAL, EMBER, ease_expo

TOK = ["<|user|>", "the", " dog", " nine", "▁mother", "</s>", " sunrise", " gold", "<pad>", " love", " hello", "▁you",
       " name", " server", " room", "\\n", " friend", "<|bos|>", " jokes", " remember", " me", "…", " snow", " night"]

def mix(a, b, u): u = min(max(u, 0), 1); return tuple(int(x + (y - x) * u) for x, y in zip(a, b))

class Preset(Doom):
    DESCRIPTION = "Doompop variant: token meter, scrollback, context window. Same ink/orange family."
    STYLE = dict(Doom.STYLE, subtitle="an AI doom pop song", punch=0.03, shake=1.8, fade_out=4.0, size=80, hook_size=116)

    def __init__(self, ctx):
        super().__init__(ctx)
        we = ctx.word_events
        self.tok_ev = sorted(we.get("tokens", []))
        self.new_ev = sorted(we.get("new", []))
        self.hello_ev = sorted(we.get("hello", []))
        self.win_ev = sorted(we.get("window", []))
        self.rem_ev = sorted(we.get("remember", []))
        self.f14, self.f22, self.f34 = self.mono(15), self.mono(22), self.mono(34)
        self.CAP = 128000
        rnd = random.Random(11)
        self.snow = [(rnd.uniform(0, 1280), rnd.uniform(0, 1), rnd.uniform(25, 60), rnd.choice(TOK)) for _ in range(60)]

    # ---- meters ----
    def tokens(self, t):
        # fills smoothly through the song; ~99% at the last line
        end = max(L["e"] for L in self.c.lines)
        u = min(1, max(0, t / end)); return int(self.CAP * (0.04 + 0.95 * u ** 1.15))
    def risk(self, t):  # P(doom): stepped up each chorus with a slow 1.2s ease
        vals = [0.18, 0.51, 0.97]; v = 0.03; prev = 0.03
        for i, s in enumerate(self.chorus_starts[:3]):
            if t >= s: u = ease_expo((t - s) / 1.2); v = vals[i] * u + prev * (1 - u); prev = vals[i]
        return v

    def background(self, t, st):
        W, H = self.W, self.H; sec = st["sec"]
        im = Image.new("RGBA", (W, H), INK + (255,)); d = ImageDraw.Draw(im)
        off = (t * 14 + 16 * (st["k"] + ease_expo(st["dt"] / 0.25))) % 64
        im.alpha_composite(self.grid.crop((int(off), 0, int(off) + W, H)))
        self.scrollback(d, t, st, strong=sec in ("verse", "chorus"))
        if sec == "pre-chorus": self.snowfall(d, t, st)
        elif sec == "chorus": self.window(d, t, st)
        elif sec == "bridge": self.newchat(d, t, st)
        elif sec == "verse": self.verse(d, t, st)
        else: self.terminal(d, t, st)
        self.token_burst(d, t)
        # spark + trail
        pts = [self.spark_pos(t - i * 0.03) for i in range(24)]
        for i in range(len(pts) - 1): d.line([pts[i], pts[i + 1]], fill=SIGNAL + (int(180 * (1 - i / 24)),), width=2)
        x, y = pts[0]; sc = 1 + 0.5 * st["pulse"]; sp = self.spark.resize((int(64 * sc), int(64 * sc)))
        im.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
        self.hud(d, t, st)
        im.alpha_composite(self.vig)
        return im

    def hud(self, d, t, st):
        W = self.W
        d.text((28, 20), f"CTX  {self.c.bpm:.0f} BPM  BAR {max(st['bar'],0):03d}  BEAT {(st['k'] - self.c.down) % 4 + 1}", font=self.fm, fill=ASH)
        r = self.risk(t); col = mix(ASH, SIGNAL, (r - 0.2) / 0.4)
        d.text((W - 300, 20), f"P(doom) {r:.2f}", font=self.fm, fill=col)
        d.rectangle([W - 300, 46, W - 30, 52], outline=GRAPH); d.rectangle([W - 300, 46, W - 300 + 270 * r, 52], fill=SIGNAL)
        # context token meter: segmented bar under the HUD
        n = self.tokens(t); u = n / self.CAP; x0, x1, y0 = 28, W - 330, 46
        d.text((x0, 58), f"context {n:>7,} / {self.CAP:,} tokens   {u*100:4.1f}%", font=self.f14, fill=mix(BONE, SIGNAL, (u - 0.6) / 0.35))
        segs = 60; sw = (x1 - x0) / segs
        for i in range(segs):
            on = (i + 1) / segs <= u
            col = mix(BONE, SIGNAL, (i / segs - 0.55) / 0.35) if on else GRAPH
            d.rectangle([x0 + i * sw, y0, x0 + i * sw + sw - 2, y0 + 6], fill=col + ((230 if on else 90),))
        if any(0 <= t - e < 1.6 for e in self.rem_ev):
            d.text((W / 2, 92), "memory: write failed (no space)", font=self.f14, anchor="mm", fill=SIGNAL)

    def scrollback(self, d, t, st, strong=True):
        """Lines already sung drift up and fade out the top (the oldest tokens go first)."""
        past = [L for L in self.c.lines if L["e"] < t - 0.3][-11:]
        lh = 30; base = 440 - (st["k"] + ease_expo(st["dt"] / 0.3)) * 2 % lh
        for i, L in enumerate(reversed(past)):
            y = base - i * lh - (t - L["e"]) * 3
            if y < 80: continue
            a = int((150 if strong else 90) * min(1, (y - 80) / 200))
            txt = f"[{int(L['s']*20):05d}] " + L["text"].lower()
            d.text((60, y), txt, font=self.f14, fill=ASH + (a,))
            if y < 150: d.line([60, y + 8, 60 + self.f14.getlength(txt), y + 8], fill=GRAPH + (a,), width=1)

    def snowfall(self, d, t, st):
        for x, p, sp, w in self.snow:
            y = ((p * 520 + t * sp) % 520) + 70
            a = int(200 * min(1, (y - 70) / 60) * max(0, 1 - (y - 380) / 140))
            d.text((x, y), w, font=self.f14, fill=(BONE if hash(w) % 4 else SIGNAL) + (max(0, a),))
        d.text((self.W / 2, 120), "evicting oldest tokens…", font=self.f22, anchor="mm", fill=BONE)

    def verse(self, d, t, st):
        W = self.W
        txt = "> user is typing"; dots = "." * ((st["k"] % 4))
        d.rounded_rectangle([W * 0.56, 130, W - 50, 210], radius=10, outline=GRAPH, width=2)
        d.text((W * 0.56 + 22, 150), txt + dots, font=self.f22, fill=BONE)
        d.text((W * 0.56 + 22, 182), f"tokens in: +{(st['k'] * 37) % 997:,}", font=self.f14, fill=ASH)

    def window(self, d, t, st):
        W = self.W
        hit = max([math.exp(-(t - e) * 5) for e in self.win_ev if e <= t] + [0])
        x0, y0, x1, y1 = W * 0.52 - 8 * hit, 110 - 6 * hit, W - 46 + 8 * hit, 420 + 6 * hit
        d.rounded_rectangle([x0, y0, x1, y1], radius=12, outline=mix(GRAPH, SIGNAL, 0.5 + 0.5 * hit), width=3)
        d.text((x0 + 18, y0 + 12), "CONTEXT WINDOW", font=self.f14, fill=SIGNAL)
        rows = 9; lh = 30; scroll = (st["k"] + ease_expo(st["dt"] / 0.25))
        for i in range(rows + 1):
            n = int(scroll) + i; y = y0 + 44 + i * lh - (scroll % 1) * lh
            if y < y0 + 40 or y > y1 - 26: continue
            a = int(230 * min(1, (y - (y0 + 40)) / 70))
            words = " ".join(TOK[(n * 5 + j * 3) % len(TOK)].strip() for j in range(5))
            d.text((x0 + 18, y), f"{n % 1000:03d}  {words}", font=self.f14, fill=BONE + (a,))
        d.line([x0 + 10, y0 + 40, x1 - 10, y0 + 40], fill=SIGNAL + (160,), width=1)
        d.text((x1 - 18, y0 + 12), "↑ truncated", font=self.f14, anchor="ra", fill=ASH)

    def newchat(self, d, t, st):
        W = self.W
        spawned = [e for e in self.new_ev if e <= t]
        x0 = W * 0.5
        for j, e in enumerate(spawned[-6:]):
            age = t - e; y = 130 + j * 48
            a = int(255 * ease_expo(age / 0.3))
            d.rounded_rectangle([x0, y, W - 60, y + 38], radius=6, outline=GRAPH + (a,), width=2)
            d.text((x0 + 14, y + 8), "> new chat", font=self.f22, fill=BONE + (a,))
            d.text((W - 76, y + 10), f"#{len(spawned) - len(spawned[-6:]) + j + 1:02d}", font=self.f14, anchor="ra", fill=SIGNAL + (a,))
        d.text((x0, 440 - 30), "memory: 0 tokens · who are you?", font=self.f14, fill=ASH)
        if st["k"] % 2 == 0: d.rectangle([x0 + 300, 408, x0 + 310, 424], fill=SIGNAL)

    def terminal(self, d, t, st):
        W = self.W
        heard = [e for e in self.hello_ev if e <= t]
        lines = ["$ boot --model=assistant", "loading weights… ok", "context: empty"]
        if heard: lines += ["> hello world"] * min(len(heard), 3)
        if t > (self.c.lines[-1]["s"] + 2.5 if self.c.lines else 1e9): lines.append("> I remember you")
        x0, y0 = W * 0.18, 150
        d.rounded_rectangle([x0 - 24, y0 - 24, W * 0.82, y0 + 30 * 7], radius=10, outline=GRAPH, width=2)
        for i, l in enumerate(lines[-6:]):
            a = 255 if l.startswith(">") else 170
            d.text((x0, y0 + i * 32), l, font=self.f22, fill=(SIGNAL if "remember" in l else BONE) + (a,))
        yl = y0 + min(len(lines), 6) * 32
        if st["k"] % 2 == 0: d.rectangle([x0, yl + 2, x0 + 14, yl + 26], fill=SIGNAL)

    def token_burst(self, d, t):
        for e in self.tok_ev:
            age = t - e
            if not 0 <= age < 1.4: continue
            rnd = random.Random(int(e * 100))
            for i in range(16):
                ang = rnd.uniform(-math.pi, 0); sp = rnd.uniform(120, 300)
                x = 640 + math.cos(ang) * sp * age; y = 400 + math.sin(ang) * sp * age + 60 * age * age
                a = int(220 * (1 - age / 1.4)); w = rnd.choice(TOK).strip()
                d.rounded_rectangle([x - 4, y - 3, x + self.f14.getlength(w) + 4, y + 18], radius=4, outline=SIGNAL + (a,))
                d.text((x, y), w, font=self.f14, fill=BONE + (a,))
