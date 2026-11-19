"""Light/Dark mode: replace hard-coded hex colors with var(--c-<hex>) tokens
and generate static/css/theme.css (light values in :root, dark values in
[data-theme="dark"]). Rules: creatorly-dark-light-mode.md.

  .venv\\Scripts\\python.exe scripts\\dev\\tokenize_colors.py

Idempotent: already tokenized colors are left as is; theme.css is regenerated
from every var(--c-xxxxxx) found in static/ and templates/.
"""
import colorsys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ["main", "home", "analytics", "competitors", "finance"]
JS = ["home", "analytics", "competitors", "finance", "finance-year"]
HTML = ["home", "finance", "analytics", "competitors"]

# Values fixed by the spec (dark side). Everything else is computed.
FIXED_DARK = {
    "ffffff": "#151C2C", "f4f6fa": "#0B1120", "f5f7fb": "#0B1120", "f8fafc": "#1B2435",
    "f1f5f9": "#1B2435", "e2e8f0": "#27324A", "eef1f5": "#222C3F", "0f172a": "#DEE2EC",
    "334155": "#93A4BE", "475569": "#98A5B9", "5b6577": "#979CA5", "1d4ed8": "#6689EA",
    "047857": "#57F9CB", "c2410c": "#F5885C", "dbeafe": "#1A2D47", "dcfce7": "#1A472A",
    "ffedd5": "#49351B", "e9ecf3": "#27324A", "ecfdf5": "#1B2435", "ecfeff": "#1B2435",
    "eef2ff": "#1B2435", "eff6ff": "#1B2435", "f5f3ff": "#1B2435", "f8faff": "#151C2C",
    "fdf2f8": "#1B2435", "fff7ed": "#1B2435",
}

HEX = re.compile(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")
DECL = re.compile(r"(?<![\w-])(--[\w-]+|[a-z-]+)\s*:\s*([^;{}\"]+)")
ATTR = re.compile(r"\b(fill|stroke|stop-color|color)=([\"'])(#[0-9A-Fa-f]{3,6})\2")
WHITE_RGBA = re.compile(r"rgba\(\s*255\s*,\s*255\s*,\s*255\s*,")


def norm(h):
    h = h.lower()
    return "".join(c * 2 for c in h) if len(h) == 3 else h


def hls(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b), (max(r, g, b) - min(r, g, b)) * 255


def to_hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def is_light(h):
    return hls(h)[0][1] >= 0.86


def is_dark(h):
    return hls(h)[0][1] < 0.5


def is_neutral(h):
    return hls(h)[1] < 40


def dark_value(h):
    if h in FIXED_DARK:
        return FIXED_DARK[h]
    (hu, l, s), chroma = hls(h)
    if l >= 0.8:
        if chroma <= 6 or (chroma <= 18 and 0.5 <= hu <= 0.72):
            if l >= 0.995:
                return "#151C2C"
            if l >= 0.955:
                return "#1B2435"
            if l >= 0.925:
                return "#222C3F"
            return "#27324A"
        return to_hex(hu, 0.17 if l > 0.95 else 0.21 if l > 0.88 else 0.27, min(s, 0.38))
    if chroma < 40:
        return to_hex(hu, min(0.92, 0.95 - 0.8 * l), min(s, 0.18))
    return to_hex(hu, 0.68, min(s, 0.8))


def tok(h):
    return f"var(--c-{h})"


def css_value(prop, value):
    """Rewrite one declaration value according to the spec rules."""
    if prop in ("filter",) or prop.startswith("--grad"):
        return value
    if prop.startswith("--"):  # page palettes (--inc-bg, --good, ...): pale bg / dark text adapt
        return HEX.sub(lambda m: tok(norm(m.group(1))) if (hls(norm(m.group(1)))[0][1] >= 0.8 or is_dark(norm(m.group(1))))
                       else m.group(0), value)
    if "shadow" in prop:  # only light hex rings (inset borders); rgba shadows stay
        return HEX.sub(lambda m: tok(norm(m.group(1))) if is_light(norm(m.group(1))) else m.group(0), value)
    textish = prop in ("color", "fill", "stroke", "caret-color", "-webkit-text-fill-color")
    bgish = prop.startswith(("background", "border", "outline")) or prop in ("stop-color",)

    def rep(m):
        h = norm(m.group(1))
        if textish and is_dark(h):
            return tok(h)
        if bgish and is_light(h):
            return tok(h)
        return m.group(0)

    value = HEX.sub(rep, value)
    if bgish:
        value = WHITE_RGBA.sub("rgba(var(--w),", value)
        value = re.sub(r"(?<![\w-])white\b", tok("ffffff"), value)
    return value


def rewrite_css(text, skip_custom=False):
    if skip_custom:  # main.css: semantic vars are themed by hand ([data-theme="dark"] block)
        return DECL.sub(lambda m: m.group(0) if m.group(1).startswith("--")
                        else m.group(0).replace(m.group(2), css_value(m.group(1), m.group(2)), 1), text)
    return DECL.sub(lambda m: m.group(0).replace(m.group(2), css_value(m.group(1), m.group(2)), 1), text)


def rewrite_inline(text):
    """CSS declarations inside style="..." / template strings, SVG attributes,
    and bare pale literals (backgrounds passed through data)."""
    text = DECL.sub(lambda m: m.group(0).replace(m.group(2), css_value(m.group(1), m.group(2)), 1), text)

    def attr(m):
        h = norm(m.group(3)[1:])
        name = m.group(1)
        # charts: only pale or neutral-dark colors adapt
        if is_light(h) or (is_dark(h) and is_neutral(h)):
            return f"{name}={m.group(2)}{tok(h)}{m.group(2)}"
        return m.group(0)

    text = ATTR.sub(attr, text)

    # [bg, fg] pairs: pale bg + dark text (avatars) adapt together;
    # pale + saturated pairs are decorative gradients (post thumbnails) and stay.
    def pair(m):
        a, b = norm(m.group(2)), norm(m.group(4))
        sep = m.group(3)
        if is_light(a) and hls(b)[0][1] < 0.45:
            return f"{m.group(1)}\"{tok(a)}\"{sep}\"{tok(b)}\"{m.group(5)}"
        if is_light(a) and 0.45 <= hls(b)[0][1] < 0.7:
            return f"{m.group(1)}\"#!{m.group(2)}\"{sep}\"#!{m.group(4)}\"{m.group(5)}"
        return m.group(0)

    text = re.sub(r"([\[(]|,\s*)\"#([0-9A-Fa-f]{6})\"(,\s*)\"#([0-9A-Fa-f]{6})\"([\]),])", pair, text)

    def bare(m):
        h = norm(m.group(2))
        if is_light(h) or (is_dark(h) and is_neutral(h)):
            return f"{m.group(1)}{tok(h)}{m.group(3)}"
        return m.group(0)

    text = re.sub(r"([\"'])#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})([\"'])", bare, text)
    return text.replace("#!", "#")


def main():
    targets = [(ROOT / "static/css" / f"{n}.css", (lambda t, n=n: rewrite_css(t, n == "main"))) for n in CSS]
    targets += [(ROOT / "static/js" / f"{n}.js", rewrite_inline) for n in JS]
    targets += [(ROOT / "templates" / f"{n}.html", rewrite_inline) for n in HTML]
    for path, fn in targets:
        src = path.read_text(encoding="utf-8")
        out = fn(src)
        if out != src:
            path.write_text(out, encoding="utf-8")
            print("updated", path.relative_to(ROOT))

    used = set()
    for p in list((ROOT / "static").rglob("*.*")) + list((ROOT / "templates").rglob("*.html")):
        if p.suffix in (".css", ".js", ".html") and p.name != "theme.css":
            used |= set(re.findall(r"var\(--c-([0-9a-f]{6})\)", p.read_text(encoding="utf-8")))
    used |= set(FIXED_DARK)
    used = sorted(used)
    light = "\n".join(f"  --c-{h}: #{h.upper()};" for h in used)
    dark = "\n".join(f"  --c-{h}: {dark_value(h)};" for h in used)
    (ROOT / "static/css/theme.css").write_text(
        "/* Creatorly â€” Light/Dark color tokens. GENERATED by scripts/dev/tokenize_colors.py â€” do not edit by hand.\n"
        "   Rules: brand gradients, chart line colors and shadows are not tokenized. */\n"
        f":root {{\n  --w: 255, 255, 255;\n  --k: 15, 23, 42;\n{light}\n}}\n"
        f'[data-theme="dark"] {{\n  color-scheme: dark;\n  --w: 30, 41, 59;\n  --k: 226, 232, 240;\n{dark}\n}}\n',
        encoding="utf-8")
    print("theme.css:", len(used), "tokens")


if __name__ == "__main__":
    main()
