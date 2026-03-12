from pathlib import Path
import math


def svg_wrap(content: str, width: int = 512, height: int = 512, bg: str = "black") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="{bg}"/>
{content}
</svg>
"""


def svg_spiral(width: int = 512, height: int = 512) -> str:
    cx = width // 2
    cy = height // 2
    pts = []
    for i in range(220):
        t = i * 0.22
        r = 6 + i * 0.9
        x = cx + math.cos(t) * r
        y = cy + math.sin(t) * r
        pts.append(f"{x:.2f},{y:.2f}")
    poly = " ".join(pts)
    return svg_wrap(
        f'<polyline points="{poly}" fill="none" stroke="cyan" stroke-width="2"/>',
        width,
        height,
    )


def svg_grid(width: int = 512, height: int = 512, step: int = 32) -> str:
    lines = []
    for x in range(0, width + 1, step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#224" stroke-width="1"/>')
    for y in range(0, height + 1, step):
        lines.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#224" stroke-width="1"/>')
    lines.append(f'<rect x="32" y="32" width="{width-64}" height="{height-64}" fill="none" stroke="gold" stroke-width="2"/>')
    return svg_wrap("\n".join(lines), width, height)


def svg_orbit(width: int = 512, height: int = 512) -> str:
    cx = width // 2
    cy = height // 2
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="16" fill="gold"/>',
        f'<circle cx="{cx}" cy="{cy}" r="64" fill="none" stroke="#3af" stroke-width="2"/>',
        f'<circle cx="{cx}" cy="{cy}" r="128" fill="none" stroke="#6cf" stroke-width="2"/>',
        f'<circle cx="{cx}" cy="{cy}" r="192" fill="none" stroke="#9ff" stroke-width="2"/>',
        f'<circle cx="{cx+64}" cy="{cy}" r="8" fill="white"/>',
        f'<circle cx="{cx-128}" cy="{cy}" r="10" fill="#8ff"/>',
        f'<circle cx="{cx}" cy="{cy-192}" r="12" fill="#f8f"/>',
    ]
    return svg_wrap("\n".join(parts), width, height)




import random

def svg_random(width: int = 512, height: int = 512) -> str:
    cx = width // 2
    cy = height // 2

    parts = []

    # random orbit rings
    for _ in range(random.randint(3,8)):
        r = random.randint(30,220)
        color = f"#{random.randint(0,0xFFFFFF):06x}"
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="2"/>'
        )

    # random planets
    for _ in range(random.randint(4,10)):
        x = random.randint(0,width)
        y = random.randint(0,height)
        size = random.randint(4,14)
        color = f"#{random.randint(0,0xFFFFFF):06x}"

        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{size}" fill="{color}"/>'
        )

    return svg_wrap("\n".join(parts), width, height)



def svg_wave(width: int = 512, height: int = 512) -> str:
    import math

    lines = []
    mid = height // 2

    for band in range(3):
        pts = []
        amp = 30 + band * 28
        freq = 0.018 + band * 0.006
        phase = band * 1.2

        for x in range(0, width + 1, 4):
            y = mid + math.sin(x * freq + phase) * amp
            pts.append(f"{x:.2f},{y:.2f}")

        color = ["#66ccff", "#ff66cc", "#ffee66"][band]
        poly = " ".join(pts)
        lines.append(
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>'
        )

    lines.append(f'<line x1="0" y1="{mid}" x2="{width}" y2="{mid}" stroke="#223344" stroke-width="1"/>')
    return svg_wrap("\n".join(lines), width, height)


def svg_phyllotaxis(width: int = 512, height: int = 512) -> str:
    import math

    cx = width / 2
    cy = height / 2
    golden = math.pi * (3 - math.sqrt(5))

    parts = []
    for n in range(260):
        r = 7.2 * math.sqrt(n)
        theta = n * golden
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        size = 2 + (n % 5)
        color = f"hsl({(n * 7) % 360}, 80%, 65%)"
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="{color}" />'
        )

    return svg_wrap("\n".join(parts), width, height)

def svg_art_text(mode: str = "spiral") -> str:
    mode = str(mode or "spiral").strip().lower()
    if mode == "grid":
        return svg_grid()
    if mode == "orbit":
        return svg_orbit()
    if mode == "random":
        return svg_random()
    if mode == "wave":
        return svg_wave()
    if mode == "phyllotaxis":
        return svg_phyllotaxis()
    return svg_spiral()


def write_art_html_viewer(svg_path: str = "andy_art.svg", html_path: str = "andy_art.html") -> str:
    svg_text = Path(svg_path).read_text(encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANDY AI Art Viewer</title>
<style>
body {{
    margin: 0;
    background: #0b1020;
    color: #e5f0ff;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    min-height: 100vh;
}}
.wrap {{
    width: 100%;
    max-width: 900px;
    padding: 20px;
    box-sizing: border-box;
}}
.card {{
    background: #111933;
    border: 1px solid #243055;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}}
h1 {{
    font-size: 22px;
    margin: 0 0 12px 0;
}}
p {{
    opacity: 0.9;
}}
.viewer {{
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 12px;
    padding: 8px;
}}
.viewer svg {{
    display: block;
    width: 100%;
    height: auto;
    background: #000;
}}
.path {{
    margin-top: 10px;
    font-size: 13px;
    opacity: 0.8;
    word-break: break-all;
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>ANDY AI Art Viewer</h1>
    <p>Structured SVG output generated by AndyAI.</p>
    <div class="viewer">
      {svg_text}
    </div>
    <div class="path">SVG: {svg_path}</div>
  </div>
</div>
</body>
</html>
"""
    Path(html_path).write_text(html, encoding="utf-8")
    return html_path


def art_artifact_summary(state, mode: str, svg_path: str, html_path: str = "") -> str:
    st = state.get("internal_state", {})
    emo_fn = state.get("ensure_emotional_state")
    emo = emo_fn(state) if callable(emo_fn) else {}

    return (
        f"type=art_artifact | mode={mode} | svg={svg_path} | html={html_path} | "
        f"goal={str(st.get('current_goal', '') or '')[:80]} | "
        f"recovery_mode={st.get('recovery_mode_type', 'standard')} | "
        f"pressure={st.get('reflex_fault_pressure', 0.0)} | "
        f"emotion[c={emo.get('confidence', 0.0)},f={emo.get('frustration', 0.0)},"
        f"q={emo.get('curiosity', 0.0)},s={emo.get('stability', 0.0)}]"
    )


def store_art_artifact_memory(state, mode: str, svg_path: str, html_path: str = ""):
    db = state.get("db", [])
    embedder = state.get("embedder")
    add_entry_fn = state.get("add_entry")
    save_db_fn = state.get("save_db")
    db_path = state.get("DB_PATH")

    if not callable(add_entry_fn):
        return

    text = art_artifact_summary(state, mode, svg_path, html_path)

    try:
        emb = embedder.embed(text) if embedder else None
    except Exception:
        emb = None

    add_entry_fn(
        db,
        text=text,
        embedding=emb,
        tags=["art", "art_artifact", "skill:visual", "lane:art_memory", "protected"],
    )

    if callable(save_db_fn) and db_path:
        save_db_fn(db_path, db)




import os

def next_art_path(mode: str):
    art_dir = Path("art")
    art_dir.mkdir(exist_ok=True)

    existing = sorted(art_dir.glob("art_*.svg"))

    if not existing:
        n = 1
    else:
        last = existing[-1].stem.split("_")[1]
        n = int(last) + 1

    name = f"art_{n:04d}_{mode}.svg"
    return art_dir / name


def write_svg_art(state, mode: str = "spiral", path: str = None) -> str:

    svg = svg_art_text(mode=mode)

    if path is None:
        path = str(next_art_path(mode))

    Path(path).write_text(svg, encoding="utf-8")

    html_path = "andy_art.html"
    write_art_html_viewer(svg_path=path, html_path=html_path)

    st = state.get("internal_state", {})
    st["last_art_mode"] = mode
    st["last_art_path"] = path
    st["last_art_html_path"] = html_path
    now_ts = state.get("now_ts")
    st["last_art_ts"] = now_ts() if callable(now_ts) else ""

    store_art_artifact_memory(state, mode=mode, svg_path=path, html_path=html_path)

    return path






def svg_spiral_mutant(turn_step: float = 0.22, radial_step: float = 0.9, width: int = 512, height: int = 512) -> str:
    import math
    cx = width // 2
    cy = height // 2
    pts = []
    for i in range(220):
        t = i * turn_step
        r = 6 + i * radial_step
        x = cx + math.cos(t) * r
        y = cy + math.sin(t) * r
        pts.append(f"{x:.2f},{y:.2f}")
    poly = " ".join(pts)
    return svg_wrap(
        f'<polyline points="{poly}" fill="none" stroke="cyan" stroke-width="2"/>',
        width,
        height,
    )


def svg_wave_mutant(a1: float = 30, a2: float = 58, a3: float = 86, f1: float = 0.018, f2: float = 0.024, f3: float = 0.030, width: int = 512, height: int = 512) -> str:
    import math
    lines = []
    mid = height // 2
    bands = [
        (a1, f1, 0.0, "#66ccff"),
        (a2, f2, 1.2, "#ff66cc"),
        (a3, f3, 2.4, "#ffee66"),
    ]

    for amp, freq, phase, color in bands:
        pts = []
        for x in range(0, width + 1, 4):
            y = mid + math.sin(x * freq + phase) * amp
            pts.append(f"{x:.2f},{y:.2f}")
        poly = " ".join(pts)
        lines.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>')

    lines.append(f'<line x1="0" y1="{mid}" x2="{width}" y2="{mid}" stroke="#223344" stroke-width="1"/>')
    return svg_wrap("\n".join(lines), width, height)


def svg_orbit_mutant(rings = None, planet_count: int = 4, width: int = 512, height: int = 512) -> str:
    import math
    if rings is None:
        rings = [48, 92, 148]
    cx = width // 2
    cy = height // 2
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="14" fill="gold"/>'
    ]

    ring_colors = ["#66ccff", "#99e6ff", "#66ffaa", "#ff66cc", "#ffee66"]
    for i, r in enumerate(rings):
        color = ring_colors[i % len(ring_colors)]
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="2"/>')

    for i in range(max(1, planet_count)):
        angle = (i / max(1, planet_count)) * math.pi * 2
        rr = rings[i % len(rings)]
        x = cx + math.cos(angle) * rr
        y = cy + math.sin(angle) * rr
        size = 6 + (i % 4)
        color = ring_colors[(i + 2) % len(ring_colors)]
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="{color}"/>')

    return svg_wrap("\n".join(parts), width, height)


def svg_phyllotaxis_mutant(scale: float = 7.2, count: int = 260, hue_step: int = 7, width: int = 512, height: int = 512) -> str:
    import math
    cx = width / 2
    cy = height / 2
    golden = math.pi * (3 - math.sqrt(5))
    parts = []

    for n in range(count):
        r = scale * math.sqrt(n)
        theta = n * golden
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        size = 2 + (n % 5)
        color = f"hsl({(n * hue_step) % 360}, 80%, 65%)"
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="{color}" />')

    return svg_wrap("\n".join(parts), width, height)




def structural_art_score(svg_text: str):
    import math

    score = 0.0

    # count primitives
    circles = svg_text.count("<circle")
    lines = svg_text.count("<line")
    polys = svg_text.count("<polyline")

    density = circles + lines + polys

    if density < 20:
        score += 0.2
    elif density < 80:
        score += 0.6
    else:
        score += 0.4

    # color diversity
    colors = svg_text.count("hsl(") + svg_text.count("stroke=")
    score += min(colors * 0.02, 0.25)

    # symmetry hint
    if "cx=" in svg_text and "cy=" in svg_text:
        score += 0.15

    return round(score,3)


def random_art_candidate():
    import random

    choices = []

    choices.append({
        "mode": "spiral",
        "label": "spiral_mutant",
        "svg": svg_spiral_mutant(
            turn_step=random.uniform(0.16, 0.30),
            radial_step=random.uniform(0.65, 1.25),
        ),
        "score": round(random.uniform(0.60, 0.88), 3),
    })

    choices.append({
        "mode": "wave",
        "label": "wave_mutant",
        "svg": svg_wave_mutant(
            a1=random.uniform(18, 42),
            a2=random.uniform(38, 72),
            a3=random.uniform(64, 108),
            f1=random.uniform(0.012, 0.024),
            f2=random.uniform(0.018, 0.032),
            f3=random.uniform(0.024, 0.040),
        ),
        "score": round(random.uniform(0.66, 0.90), 3),
    })

    ring_count = random.randint(2, 5)
    rings = sorted({random.randint(36, 196) for _ in range(ring_count)})
    choices.append({
        "mode": "orbit",
        "label": "orbit_mutant",
        "svg": svg_orbit_mutant(
            rings=rings,
            planet_count=random.randint(3, 7),
        ),
        "score": round(random.uniform(0.62, 0.86), 3),
    })

    choices.append({
        "mode": "phyllotaxis",
        "label": "phyllotaxis_mutant",
        "svg": svg_phyllotaxis_mutant(
            scale=random.uniform(5.8, 8.8),
            count=random.randint(180, 320),
            hue_step=random.randint(4, 13),
        ),
        "score": round(random.uniform(0.74, 0.97), 3),
    })

    choices.append({
        "mode": "random",
        "label": "random_mutant",
        "svg": svg_random(),
        "score": round(random.uniform(0.45, 0.72), 3),
    })

    return choices



def lineage_parent_mode(state) -> str:
    st = state.get("internal_state", {})
    mode = str(st.get("last_evolved_art_mode", "") or "").strip().lower()
    if mode:
        return mode
    mode = str(st.get("last_art_mode", "") or "").strip().lower()
    if mode:
        return mode
    return "phyllotaxis"




def next_species_variant_label(state, base_mode: str) -> str:
    st = state.get("internal_state", {})
    counters = dict(st.get("art_variant_counters", {}) or {})
    base_mode = str(base_mode or "").strip().lower()
    counters[base_mode] = int(counters.get(base_mode, 0) or 0) + 1
    st["art_variant_counters"] = counters
    return f"{base_mode}_v{counters[base_mode]}"


def register_lineage_entry(state, base_mode: str, variant_label: str, score: float, path: str):
    st = state.get("internal_state", {})
    lineage = list(st.get("art_lineage_log", []) or [])
    lineage.append({
        "base_mode": str(base_mode or ""),
        "variant": str(variant_label or ""),
        "score": float(score or 0.0),
        "path": str(path or ""),
    })
    st["art_lineage_log"] = lineage[-50:]
    return lineage


def art_lineage_text(state) -> str:
    st = state.get("internal_state", {})
    lineage = list(st.get("art_lineage_log", []) or [])

    lines = ["ART LINEAGE", ""]
    if not lineage:
        lines.append("No lineage entries yet.")
        return "\n".join(lines)

    for i, entry in enumerate(lineage[-20:], start=1):
        lines.append(
            f"{i:02d}. {entry.get('base_mode', '')} -> {entry.get('variant', '')} | "
            f"score={entry.get('score', '')} | {entry.get('path', '')}"
        )

    return "\n".join(lines)


def svg_burst_mutant():
    import math, random
    cx, cy = 256, 256
    rays = random.randint(20, 48)
    radius = random.randint(140, 220)
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{random.randint(10,18)}" fill="gold" />']
    for i in range(rays):
        ang = (math.pi * 2 * i) / rays
        x2 = cx + math.cos(ang) * radius
        y2 = cy + math.sin(ang) * radius
        color = f"hsl({(i * random.randint(7,15)) % 360}, 85%, 65%)"
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{random.randint(1,3)}"/>')
        if random.random() < 0.7:
            x3 = cx + math.cos(ang) * (radius + random.randint(8, 28))
            y3 = cy + math.sin(ang) * (radius + random.randint(8, 28))
            parts.append(f'<circle cx="{x3:.2f}" cy="{y3:.2f}" r="{random.randint(3,7)}" fill="{color}" />')
    return svg_wrap("\n".join(parts), 512, 512)


def svg_drift_mutant():
    import random
    parts = []
    for i in range(random.randint(140, 240)):
        x = random.randint(50, 462)
        y = random.randint(50, 462)
        r = random.randint(2, 9)
        color = f"hsl({(i * random.randint(5,13)) % 360}, 80%, 65%)"
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" />')
    for i in range(random.randint(18, 40)):
        x1 = random.randint(50, 462)
        y1 = random.randint(50, 462)
        x2 = x1 + random.randint(-100, 100)
        y2 = y1 + random.randint(-100, 100)
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#223344" stroke-width="1"/>')
    return svg_wrap("\n".join(parts), 512, 512)


def svg_lattice_mutant():
    import random
    parts = []
    step = random.choice([36, 42, 48, 54])
    start = random.choice([60, 72, 84])
    end = 512 - start
    for x in range(start, end + 1, step):
        for y in range(start, end + 1, step):
            rr = random.randint(4, 8)
            hue = (x * 3 + y * 5 + random.randint(0, 40)) % 360
            parts.append(f'<circle cx="{x}" cy="{y}" r="{rr}" fill="hsl({hue}, 80%, 65%)" />')
    for x in range(start, end + 1, step):
        parts.append(f'<line x1="{x}" y1="{start}" x2="{x}" y2="{end}" stroke="#335577" stroke-width="1"/>')
    for y in range(start, end + 1, step):
        parts.append(f'<line x1="{start}" y1="{y}" x2="{end}" y2="{y}" stroke="#335577" stroke-width="1"/>')
    return svg_wrap("\n".join(parts), 512, 512)


def svg_rings_mutant():
    import random
    parts = []
    ring_count = random.randint(4, 7)
    base = random.randint(24, 40)
    gap = random.randint(24, 38)
    colors = ["#66ccff", "#66ffaa", "#ff66cc", "#ffee66", "#a78bfa", "#f97316", "#34d399"]
    radii = [base + i * gap for i in range(ring_count)]
    for i, r in enumerate(radii):
        c = colors[i % len(colors)]
        parts.append(f'<circle cx="256" cy="256" r="{r}" fill="none" stroke="{c}" stroke-width="{random.randint(2,4)}"/>')
        if random.random() < 0.8:
            parts.append(f'<circle cx="{256+r}" cy="256" r="{random.randint(5,9)}" fill="{c}" />')
    parts.append(f'<circle cx="256" cy="256" r="{random.randint(8,14)}" fill="gold" />')
    return svg_wrap("\n".join(parts), 512, 512)


def mutate_discovered_species(state, base_mode: str):
    base_mode = str(base_mode or "").strip().lower()
    label = next_species_variant_label(state, base_mode)

    if base_mode == "burst":
        svg = svg_burst_mutant()
    elif base_mode == "drift":
        svg = svg_drift_mutant()
    elif base_mode == "lattice":
        svg = svg_lattice_mutant()
    elif base_mode == "rings":
        svg = svg_rings_mutant()
    else:
        candidate = candidate_from_discovered_mode(base_mode)
        if not candidate:
            return None
        svg = candidate["svg"]

    return {
        "mode": base_mode,
        "label": label,
        "svg": svg,
        "base_mode": base_mode,
        "variant": True,
    }

def candidate_from_discovered_mode(mode: str):
    import random

    mode = str(mode or "").strip().lower()

    if mode == "lattice":
        return {
            "mode": "lattice",
            "label": "lattice_species",
            "svg": svg_lattice(),
        }

    if mode == "burst":
        return {
            "mode": "burst",
            "label": "burst_species",
            "svg": svg_burst(),
        }

    if mode == "rings":
        return {
            "mode": "rings",
            "label": "rings_species",
            "svg": svg_rings(),
        }

    if mode == "drift":
        return {
            "mode": "drift",
            "label": "drift_species",
            "svg": svg_drift(),
        }

    return None


def discovered_mode_pool(state):
    st = state.get("internal_state", {})
    return list(st.get("discovered_art_modes", []) or [])

def candidate_from_mode(mode: str):
    import random

    mode = str(mode or "").strip().lower()

    if mode not in valid_art_modes():
        raise ValueError(f"Unknown art mode: {mode}")

    if mode == "spiral":
        return {
            "mode": "spiral",
            "label": "spiral_lineage",
            "svg": svg_spiral_mutant(
                turn_step=random.uniform(0.18, 0.26),
                radial_step=random.uniform(0.75, 1.10),
            ),
        }

    if mode == "wave":
        return {
            "mode": "wave",
            "label": "wave_lineage",
            "svg": svg_wave_mutant(
                a1=random.uniform(22, 38),
                a2=random.uniform(44, 68),
                a3=random.uniform(70, 98),
                f1=random.uniform(0.014, 0.022),
                f2=random.uniform(0.020, 0.030),
                f3=random.uniform(0.026, 0.036),
            ),
        }

    if mode == "orbit":
        ring_count = random.randint(2, 4)
        rings = sorted({random.randint(44, 170) for _ in range(ring_count)})
        return {
            "mode": "orbit",
            "label": "orbit_lineage",
            "svg": svg_orbit_mutant(
                rings=rings,
                planet_count=random.randint(3, 6),
            ),
        }

    if mode == "phyllotaxis":
        return {
            "mode": "phyllotaxis",
            "label": "phyllotaxis_lineage",
            "svg": svg_phyllotaxis_mutant(
                scale=random.uniform(6.4, 8.1),
                count=random.randint(220, 300),
                hue_step=random.randint(5, 10),
            ),
        }

    if mode == "random":
        return {
            "mode": "random",
            "label": "random_lineage",
            "svg": svg_random(),
        }

    return candidate_from_mode("phyllotaxis")


def guarded_art_score(state, mode: str, svg_text: str) -> float:
    base = simple_structure_score(svg_text)
    coherence = simple_coherence_score(mode, svg_text)
    nervous = nervous_art_bias(state, mode, svg_text)
    repeat = repeat_penalty(state, mode)
    return round(base + coherence + nervous - repeat, 3)




def art_emotion_snapshot(state):
    st = state.get("internal_state", {}) or {}

    emo = st.get("emotional_state", {}) or {}
    if isinstance(emo, dict) and emo:
        return {
            "confidence": float(emo.get("confidence", 0.0) or 0.0),
            "frustration": float(emo.get("frustration", 0.0) or 0.0),
            "curiosity": float(emo.get("curiosity", 0.0) or 0.0),
            "stability": float(emo.get("stability", 0.0) or 0.0),
        }

    emo_fn = state.get("ensure_emotional_state")
    if callable(emo_fn):
        try:
            e = emo_fn(state) or {}
            return {
                "confidence": float(e.get("confidence", 0.0) or 0.0),
                "frustration": float(e.get("frustration", 0.0) or 0.0),
                "curiosity": float(e.get("curiosity", 0.0) or 0.0),
                "stability": float(e.get("stability", 0.0) or 0.0),
            }
        except Exception:
            pass

    return {
        "confidence": 0.0,
        "frustration": 0.0,
        "curiosity": 0.0,
        "stability": 0.0,
    }


def recent_winner_modes(state, limit: int = 6):
    st = state.get("internal_state", {}) or {}
    arr = list(st.get("art_recent_winner_modes", []) or [])
    return arr[-limit:]


def push_recent_winner_mode(state, mode: str, limit: int = 6):
    st = state.get("internal_state", {}) or {}
    arr = list(st.get("art_recent_winner_modes", []) or [])
    mode = str(mode or "").strip().lower()
    if not mode:
        return
    arr.append(mode)
    if len(arr) > limit:
        arr = arr[-limit:]
    st["art_recent_winner_modes"] = arr


def repeat_penalty(state, mode: str) -> float:
    mode = str(mode or "").strip().lower()
    recent = recent_winner_modes(state, limit=6)
    repeats = sum(1 for x in recent if str(x).strip().lower() == mode)

    if repeats <= 1:
        return 0.0
    if repeats == 2:
        return 0.05
    if repeats == 3:
        return 0.10
    if repeats == 4:
        return 0.16
    return 0.22



def art_win_counts(state):
    st = state.get("internal_state", {}) or {}
    counts = dict(st.get("art_win_counts", {}) or {})
    return counts


def increment_art_win_count(state, mode: str):
    st = state.get("internal_state", {}) or {}
    counts = dict(st.get("art_win_counts", {}) or {})
    mode = str(mode or "").strip().lower()
    if not mode:
        return
    counts[mode] = int(counts.get(mode, 0) or 0) + 1
    st["art_win_counts"] = counts


def dominant_art_mode(state) -> str:
    counts = art_win_counts(state)
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[0][0]


def recent_lineage_summary(state, limit: int = 6) -> str:
    recent = recent_winner_modes(state, limit=limit)
    if not recent:
        return ""

    buckets = {}
    for mode in recent:
        m = str(mode or "").strip().lower()
        if not m:
            continue
        buckets[m] = buckets.get(m, 0) + 1

    parts = [f"{k}:{buckets[k]}" for k in sorted(buckets)]
    return ", ".join(parts)


def art_identity_summary(state) -> str:
    emo = art_emotion_snapshot(state)
    dom = dominant_art_mode(state)
    recent = recent_lineage_summary(state, limit=6)

    confidence = float(emo.get("confidence", 0.0) or 0.0)
    frustration = float(emo.get("frustration", 0.0) or 0.0)
    curiosity = float(emo.get("curiosity", 0.0) or 0.0)
    stability = float(emo.get("stability", 0.0) or 0.0)

    tone = []
    if stability >= 0.7:
        tone.append("order-seeking")
    if curiosity >= 0.6:
        tone.append("exploratory")
    if confidence >= 0.7:
        tone.append("confident")
    if frustration >= 0.6:
        tone.append("tense")

    tone_text = ", ".join(tone) if tone else "neutral"

    if dom:
        return f"Dominant style: {dom}. Recent trend: {recent or 'none'}. Current visual temperament: {tone_text}."
    return f"No dominant style yet. Current visual temperament: {tone_text}."



def backfill_win_counts(state):
    st = state.get("internal_state", {}) or {}

    if st.get("art_win_counts"):
        return

    recent = st.get("art_recent_winner_modes", [])
    counts = {}

    for m in recent:
        m = str(m).strip().lower()
        counts[m] = counts.get(m, 0) + 1

    st["art_win_counts"] = counts

def art_profile_text(state) -> str:
    backfill_win_counts(state)
    counts = art_win_counts(state)
    dom = dominant_art_mode(state)
    recent = recent_lineage_summary(state, limit=6)
    ident = art_identity_summary(state)

    lines = [
        "ART PROFILE",
        "",
        f"Dominant Mode: {dom}",
        f"Recent Trend: {recent}",
        "",
        "Win Counts:",
    ]

    if counts:
        for k in sorted(counts):
            lines.append(f"  {k}: {counts[k]}")
    else:
        lines.append("  none")

    lines.extend([
        "",
        "Identity Summary:",
        ident,
    ])

    return "\n".join(lines)


def valid_art_modes():
    return [
        "spiral",
        "wave",
        "orbit",
        "phyllotaxis",
        "random",
    ]


def art_modes_text():
    modes = valid_art_modes()

    lines = [
        "ART MODES",
        "",
        "Generators:",
    ]

    for m in modes:
        lines.append(f"  {m}")

    lines.extend([
        "",
        "Commands:",
        "  evolve",
        "  evolve <rounds>",
        "  invent",
        "  gallery",
        "  profile",
        "  status",
        "  memory",
        "  discovered",
        "  species",
        "  best",
        "  hof",
        "  history",
        "  lineage",
        "  family <mode> <rounds>",
        "  vocab",
        "  scene <concepts...>",
        "  scene evolve <concepts...> <rounds>",
    ])

    return "\n".join(lines)


def simple_structure_score(svg_text: str) -> float:
    circles = svg_text.count("<circle")
    lines = svg_text.count("<line")
    polys = svg_text.count("<polyline")

    primitives = circles + lines + polys
    score = 0.0

    if primitives < 8:
        score += 0.18
    elif primitives < 40:
        score += 0.55
    elif primitives < 140:
        score += 0.72
    else:
        score += 0.48

    kinds = 0
    if circles > 0:
        kinds += 1
    if lines > 0:
        kinds += 1
    if polys > 0:
        kinds += 1
    score += kinds * 0.08

    colors = svg_text.count("stroke=") + svg_text.count("fill=") + svg_text.count("hsl(")
    score += min(colors * 0.01, 0.22)

    return round(score, 3)


def simple_coherence_score(mode: str, svg_text: str) -> float:
    mode = str(mode or "").strip().lower()
    circles = svg_text.count("<circle")
    lines = svg_text.count("<line")
    polys = svg_text.count("<polyline")

    score = 0.0

    if mode == "spiral":
        if polys >= 1:
            score += 0.14
        if circles <= 6:
            score += 0.05

    elif mode == "wave":
        if polys >= 2:
            score += 0.14
        if circles == 0:
            score += 0.05

    elif mode == "orbit":
        if circles >= 4:
            score += 0.14
        if lines == 0:
            score += 0.05

    elif mode == "phyllotaxis":
        if circles >= 80:
            score += 0.16
        if "hsl(" in svg_text:
            score += 0.06

    elif mode == "random":
        if circles >= 4:
            score += 0.04

    elif mode == "scene":
        if circles >= 1 or lines >= 1:
            score += 0.10
        if polys >= 1 or lines >= 2:
            score += 0.08

    return round(score, 3)


def nervous_art_bias(state, mode: str, svg_text: str) -> float:
    emo = art_emotion_snapshot(state)

    curiosity = float(emo.get("curiosity", 0.5) or 0.5)
    frustration = float(emo.get("frustration", 0.0) or 0.0)
    stability = float(emo.get("stability", 0.5) or 0.5)
    confidence = float(emo.get("confidence", 0.5) or 0.5)

    circles = svg_text.count("<circle")
    lines = svg_text.count("<line")
    polys = svg_text.count("<polyline")
    primitives = circles + lines + polys

    bias = 0.0

    diversity = 0
    if circles > 0:
        diversity += 1
    if lines > 0:
        diversity += 1
    if polys > 0:
        diversity += 1
    bias += curiosity * diversity * 0.03

    if primitives > 120:
        bias -= frustration * 0.16
    elif primitives > 60:
        bias -= frustration * 0.08

    if mode in ("phyllotaxis", "orbit", "wave"):
        bias += stability * 0.06

    if 20 <= primitives <= 120:
        bias += confidence * 0.05

    return round(bias, 3)


def guarded_art_score(state, mode: str, svg_text: str) -> float:
    base = simple_structure_score(svg_text)
    coherence = simple_coherence_score(mode, svg_text)
    nervous = nervous_art_bias(state, mode, svg_text)
    repeat = repeat_penalty(state, mode)
    return round(base + coherence + nervous - repeat, 3)



def write_art_gallery_browser(limit: int = 30, html_path: str = "art_gallery.html") -> str:
    art_dir = Path("art")
    art_dir.mkdir(exist_ok=True)

    files = sorted(art_dir.glob("art_*.svg"))[-limit:]

    cards = []
    for f in files:
        try:
            svg = f.read_text(encoding="utf-8")
        except Exception:
            continue

        cards.append(f"""
        <div class="card">
          <div class="meta">{f.name}</div>
          <div class="viewer">{svg}</div>
        </div>
        """)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANDY AI Art Gallery</title>
<style>
body {{
    margin: 0;
    background: #0b1020;
    color: #e5f0ff;
    font-family: Arial, sans-serif;
}}
.wrap {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 16px;
}}
h1 {{
    margin: 0 0 8px 0;
    font-size: 28px;
}}
p {{
    margin: 0 0 18px 0;
    opacity: 0.85;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
}}
.card {{
    background: #111933;
    border: 1px solid #243055;
    border-radius: 16px;
    padding: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}}
.meta {{
    font-size: 13px;
    opacity: 0.8;
    margin-bottom: 8px;
    word-break: break-all;
}}
.viewer {{
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    padding: 6px;
}}
.viewer svg {{
    display: block;
    width: 100%;
    height: auto;
    background: #000;
}}
</style>
</head>
<body>
<div class="wrap">
  <h1>ANDY AI Art Gallery</h1>
  <p>Recent saved SVG artifacts generated by AndyAI.</p>
  <div class="grid">
    {''.join(cards)}
  </div>
</div>
</body>
</html>
"""
    Path(html_path).write_text(html, encoding="utf-8")
    return html_path



def svg_lattice(width: int = 512, height: int = 512) -> str:
    parts = []
    for x in range(80, 433, 48):
        for y in range(80, 433, 48):
            parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="hsl({(x+y)%360}, 80%, 65%)" />')
    for x in range(80, 433, 48):
        parts.append(f'<line x1="{x}" y1="80" x2="{x}" y2="432" stroke="#335577" stroke-width="1"/>')
    for y in range(80, 433, 48):
        parts.append(f'<line x1="80" y1="{y}" x2="432" y2="{y}" stroke="#335577" stroke-width="1"/>')
    return svg_wrap("\n".join(parts), width, height)


def svg_burst(width: int = 512, height: int = 512) -> str:
    import math
    cx, cy = width // 2, height // 2
    parts = ['<circle cx="256" cy="256" r="14" fill="gold" />']
    for i in range(36):
        ang = (math.pi * 2 * i) / 36.0
        x2 = cx + math.cos(ang) * 180
        y2 = cy + math.sin(ang) * 180
        color = f"hsl({(i*11)%360}, 85%, 65%)"
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="2"/>')
        x3 = cx + math.cos(ang) * 200
        y3 = cy + math.sin(ang) * 200
        parts.append(f'<circle cx="{x3:.2f}" cy="{y3:.2f}" r="4" fill="{color}" />')
    return svg_wrap("\n".join(parts), width, height)


def svg_rings(width: int = 512, height: int = 512) -> str:
    parts = []
    radii = [36, 72, 108, 144, 180]
    colors = ["#66ccff", "#66ffaa", "#ff66cc", "#ffee66", "#a78bfa"]
    for r, c in zip(radii, colors):
        parts.append(f'<circle cx="256" cy="256" r="{r}" fill="none" stroke="{c}" stroke-width="3"/>')
    for i, r in enumerate(radii):
        parts.append(f'<circle cx="{256+r}" cy="256" r="8" fill="{colors[i]}" />')
    parts.append('<circle cx="256" cy="256" r="10" fill="gold" />')
    return svg_wrap("\n".join(parts), width, height)


def svg_drift(width: int = 512, height: int = 512) -> str:
    import random
    parts = []
    for i in range(180):
        x = random.randint(70, 440)
        y = random.randint(70, 440)
        r = random.randint(2, 8)
        color = f"hsl({(i*9)%360}, 80%, 65%)"
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" />')
    for i in range(24):
        x1 = random.randint(60, 450)
        y1 = random.randint(60, 450)
        x2 = x1 + random.randint(-80, 80)
        y2 = y1 + random.randint(-80, 80)
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#223344" stroke-width="1"/>')
    return svg_wrap("\n".join(parts), width, height)




def register_discovered_mode(state, mode):
    st = state.get("internal_state", {})
    discovered = st.setdefault("discovered_art_modes", [])

    if mode not in discovered:
        discovered.append(mode)

    return discovered


def discovered_modes_text(state):
    st = state.get("internal_state", {})
    modes = st.get("discovered_art_modes", [])

    if not modes:
        return "No discovered modes yet."

    lines = ["DISCOVERED ART MODES", ""]
    for m in modes:
        lines.append(f"  {m}")

    return "\n".join(lines)




def register_discovered_mode(state, mode):
    st = state.get("internal_state", {})
    discovered = st.setdefault("discovered_art_modes", [])

    if mode not in discovered:
        discovered.append(mode)

    return discovered


def discovered_modes_text(state):
    st = state.get("internal_state", {})
    modes = st.get("discovered_art_modes", [])

    if not modes:
        return "No discovered modes yet."

    lines = ["DISCOVERED ART MODES", ""]
    for m in modes:
        lines.append(f"  {m}")

    return "\n".join(lines)

def invent_art_candidate():
    import random

    choices = [
        ("lattice", svg_lattice()),
        ("burst", svg_burst()),
        ("rings", svg_rings()),
        ("drift", svg_drift()),
    ]

    mode, svg = random.choice(choices)
    return {
        "mode": mode,
        "label": f"invented_{mode}",
        "svg": svg,
    }


def write_invented_art(state):
    candidate = invent_art_candidate()
    mode = candidate["mode"]

    # register discovered style
    register_discovered_mode(state, mode)

    svg = candidate["svg"]

    art_dir = Path("art")
    art_dir.mkdir(exist_ok=True)

    path = str(next_art_path(mode))
    Path(path).write_text(svg, encoding="utf-8")

    html_path = "andy_art.html"
    write_art_html_viewer(svg_path=path, html_path=html_path)

    score = guarded_art_score(state, mode, svg)

    st = state.get("internal_state", {})
    st["last_art_mode"] = mode
    st["last_art_path"] = path
    st["last_art_html_path"] = html_path
    now_ts = state.get("now_ts")
    st["last_art_ts"] = now_ts() if callable(now_ts) else ""
    st["last_invented_art_mode"] = mode
    st["last_invented_art_score"] = score
    st["last_invented_art_path"] = path

    store_art_artifact_memory(state, mode=mode, svg_path=path, html_path=html_path)
    update_art_hall_of_fame(state, mode, score, path)

    return {
        "mode": mode,
        "path": path,
        "score": score,
    }



def evolve_art_generations(state, rounds: int = 5):
    rounds = max(1, min(int(rounds), 50))

    results = []
    best = None

    for i in range(rounds):
        evolve_art(state)

        st = state.get("internal_state", {})
        mode = str(st.get("last_evolved_art_mode", "") or "")
        path = str(st.get("last_evolved_art_path", "") or "")
        score = float(st.get("last_evolved_art_score", 0.0) or 0.0)

        item = {
            "round": i + 1,
            "mode": mode,
            "path": path,
            "score": score,
        }
        results.append(item)

        if best is None or score > best["score"]:
            best = dict(item)

    lines = [
        f"ART EVOLUTION RUN ({rounds} rounds)",
        "",
        "Rounds:",
    ]

    for r in results:
        lines.append(
            f"  {r['round']:02d}. {r['mode']} | score={r['score']} | {r['path']}"
        )

    if best:
        lines.extend([
            "",
            "BEST OVERALL:",
            f"  round={best['round']}",
            f"  mode={best['mode']}",
            f"  score={best['score']}",
            f"  path={best['path']}",
        ])

    text = "\n".join(lines)
    st = state.get("internal_state", {})
    st["last_art_evolution_run"] = text
    return text


def update_art_hall_of_fame(state, mode: str, score: float, path: str):
    st = state.get("internal_state", {})
    hof = list(st.get("art_hall_of_fame", []) or [])

    entry = {
        "mode": str(mode or ""),
        "score": float(score or 0.0),
        "path": str(path or ""),
    }

    hof.append(entry)
    hof = sorted(hof, key=lambda x: (-float(x.get("score", 0.0) or 0.0), str(x.get("mode", ""))))[:10]
    st["art_hall_of_fame"] = hof

    if hof:
        best = hof[0]
        st["best_art_mode"] = str(best.get("mode", "") or "")
        st["best_art_score"] = float(best.get("score", 0.0) or 0.0)
        st["best_art_path"] = str(best.get("path", "") or "")

    return hof


def art_best_text(state) -> str:
    st = state.get("internal_state", {})
    lines = [
        "ART BEST",
        "",
        f"Best Mode: {st.get('best_art_mode', '')}",
        f"Best Score: {st.get('best_art_score', '')}",
        f"Best Path: {st.get('best_art_path', '')}",
    ]
    return "\n".join(lines)


def art_hof_text(state) -> str:
    st = state.get("internal_state", {})
    hof = list(st.get("art_hall_of_fame", []) or [])

    lines = ["ART HALL OF FAME", ""]
    if not hof:
        lines.append("No entries yet.")
        return "\n".join(lines)

    for i, entry in enumerate(hof, start=1):
        lines.append(
            f"{i:02d}. {entry.get('mode', '')} | score={entry.get('score', '')} | {entry.get('path', '')}"
        )

    return "\n".join(lines)


def art_history_text(state) -> str:
    st = state.get("internal_state", {})
    text = str(st.get("last_art_evolution_run", "") or "").strip()

    if not text:
        return "ART HISTORY\n\nNo recorded evolution session yet."

    return text


def evolve_family_generations(state, base_mode: str, rounds: int = 5):
    base_mode = str(base_mode or "").strip().lower()
    rounds = max(1, min(int(rounds), 50))

    results = []
    best = None

    for i in range(rounds):
        cand = mutate_discovered_species(state, base_mode)
        if not cand:
            return f"ART FAMILY ERROR\n\nUnknown discovered family: {base_mode}"

        path = str(next_art_path(base_mode))
        Path(path).write_text(cand["svg"], encoding="utf-8")

        html_path = "andy_art.html"
        write_art_html_viewer(svg_path=path, html_path=html_path)

        score = guarded_art_score(state, cand["mode"], cand["svg"])

        register_lineage_entry(
            state,
            base_mode,
            str(cand.get("label", base_mode)),
            score,
            path,
        )
        update_art_hall_of_fame(state, base_mode, score, path)

        st = state.get("internal_state", {})
        st["last_art_mode"] = base_mode
        st["last_art_path"] = path
        st["last_art_html_path"] = html_path
        now_ts = state.get("now_ts")
        st["last_art_ts"] = now_ts() if callable(now_ts) else ""
        st["last_family_training_mode"] = base_mode
        st["last_family_training_label"] = str(cand.get("label", base_mode))
        st["last_family_training_score"] = score
        st["last_family_training_path"] = path

        item = {
            "round": i + 1,
            "mode": base_mode,
            "label": str(cand.get("label", base_mode)),
            "path": path,
            "score": score,
        }
        results.append(item)

        if best is None or score > best["score"]:
            best = dict(item)

    lines = [
        f"ART FAMILY TRAINING ({base_mode}, {rounds} rounds)",
        "",
        "Rounds:",
    ]

    for r in results:
        lines.append(
            f"  {r['round']:02d}. {r['label']} | score={r['score']} | {r['path']}"
        )

    if best:
        lines.extend([
            "",
            "BEST OVERALL:",
            f"  round={best['round']}",
            f"  mode={best['mode']}",
            f"  label={best['label']}",
            f"  score={best['score']}",
            f"  path={best['path']}",
        ])

    text = "\n".join(lines)
    st = state.get("internal_state", {})
    st["last_art_family_run"] = text
    return text


def visual_vocabulary():
    return {
        "moon": "large glowing moon in the sky",
        "sun": "bright circular sun",
        "star": "small star points in the sky",
        "mountain": "triangular mountain ridge",
        "tree": "simple trunk and canopy tree",
        "wolf": "stylized wolf silhouette",
        "ground": "ground line / horizon",
        "night": "dark night background",
        "river": "curved river line",
    }


def art_vocab_text() -> str:
    vocab = visual_vocabulary()
    lines = ["ART VOCAB", ""]
    for k in sorted(vocab.keys()):
        lines.append(f"  {k}: {vocab[k]}")
    return "\n".join(lines)


def primitive_moon():
    return '<circle cx="400" cy="100" r="48" fill="#f8f3c9" opacity="0.95" />'


def primitive_sun():
    return '<circle cx="400" cy="100" r="52" fill="#ffd54a" opacity="0.95" />'


def primitive_stars():
    parts = []
    pts = [(60,70), (120,40), (220,90), (310,50), (470,60), (520,120), (150,130)]
    for x, y in pts:
        parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="white" />')
    return "\n".join(parts)


def primitive_ground():
    return '<line x1="0" y1="400" x2="512" y2="400" stroke="#445566" stroke-width="3" />'


def primitive_mountain():
    return '\n'.join([
        '<polygon points="40,400 160,210 280,400" fill="#2f3d4f" />',
        '<polygon points="180,400 320,180 460,400" fill="#394b60" />',
    ])


def primitive_tree(x=120, y=400):
    trunk = f'<rect x="{x}" y="{y-70}" width="14" height="70" fill="#6b4f35" />'
    canopy = f'<circle cx="{x+7}" cy="{y-88}" r="28" fill="#2e8b57" />'
    return trunk + "\n" + canopy


def primitive_river():
    return '<path d="M 20 430 C 120 420, 180 450, 300 430 S 450 390, 512 420" stroke="#5dade2" stroke-width="6" fill="none" opacity="0.85" />'


def primitive_wolf():
    return '\n'.join([
        '<polygon points="180,360 220,300 260,320 280,290 300,310 312,350 280,372 230,376" fill="#1e1e1e" />',
        '<polygon points="255,300 268,278 278,302" fill="#1e1e1e" />',
        '<line x1="310" y1="345" x2="340" y2="320" stroke="#1e1e1e" stroke-width="6" />',
    ])


def primitive_wolf_howl():
    return '\n'.join([
        '<polygon points="180,360 220,300 255,312 282,260 308,280 320,340 286,368 230,374" fill="#1e1e1e" />',
        '<polygon points="276,262 288,238 300,266" fill="#1e1e1e" />',
        '<line x1="302" y1="270" x2="335" y2="248" stroke="#1e1e1e" stroke-width="6" />',
        '<path d="M 340 245 Q 355 235, 368 245" stroke="#cbd5e1" stroke-width="2" fill="none" opacity="0.9"/>',
        '<path d="M 346 236 Q 365 220, 382 236" stroke="#cbd5e1" stroke-width="2" fill="none" opacity="0.7"/>',
    ])


def scene_svg_from_concepts(concepts):
    concepts = [str(c).strip().lower() for c in concepts if str(c).strip()]
    bg = "#0b1020" if ("night" in concepts or "moon" in concepts or "star" in concepts) else "#dff1ff"
    parts = []

    if "sun" in concepts:
        parts.append(primitive_sun())
    if "moon" in concepts:
        parts.append(primitive_moon())
    if "star" in concepts or "night" in concepts or "moon" in concepts:
        parts.append(primitive_stars())
    if "mountain" in concepts:
        parts.append(primitive_mountain())
    if "river" in concepts:
        parts.append(primitive_river())
    if "ground" in concepts or "tree" in concepts or "wolf" in concepts or "mountain" in concepts:
        parts.append(primitive_ground())
    if "tree" in concepts:
        parts.append(primitive_tree(110, 400))
        parts.append(primitive_tree(370, 400))
    if "wolf" in concepts:
        parts.append(primitive_wolf())

    if not parts:
        parts.append('<text x="40" y="80" fill="white" font-size="22">No known scene concepts.</text>')

    return svg_wrap("\n".join(parts), 512, 512, bg=bg)


def write_scene_art(state, concepts, actions=None):
    concepts = [str(c).strip().lower() for c in concepts if str(c).strip()]
    actions = [str(a).strip().lower() for a in (actions or []) if str(a).strip()]

    svg = scene_svg_from_concepts(concepts)

    if "wolf" in concepts and "howling" in actions:
        bg = "#0b1020" if ("night" in concepts or "moon" in concepts or "star" in concepts) else "#dff1ff"
        parts = []

        if "moon" in concepts:
            parts.append(primitive_moon())
        if "star" in concepts or "night" in concepts or "moon" in concepts:
            parts.append(primitive_stars())
        if "mountain" in concepts:
            parts.append(primitive_mountain())
        if "river" in concepts:
            parts.append(primitive_river())
        if "ground" in concepts or "tree" in concepts or "wolf" in concepts or "mountain" in concepts:
            parts.append(primitive_ground())
        if "tree" in concepts:
            parts.append(primitive_tree(110, 400))
            parts.append(primitive_tree(370, 400))
        parts.append(primitive_wolf_howl())

        svg = svg_wrap("\n".join(parts), 512, 512, bg=bg)

    label_parts = concepts[:4]
    if actions:
        label_parts.extend(actions[:2])
    label = "_".join(label_parts) if label_parts else "scene"

    path = str(next_art_path(label))
    Path(path).write_text(svg, encoding="utf-8")

    html_path = "andy_art.html"
    write_art_html_viewer(svg_path=path, html_path=html_path)

    score = guarded_art_score(state, "scene", svg)

    st = state.get("internal_state", {})
    st["last_art_mode"] = "scene"
    st["last_art_path"] = path
    st["last_art_html_path"] = html_path
    now_ts = state.get("now_ts")
    st["last_art_ts"] = now_ts() if callable(now_ts) else ""
    st["last_scene_concepts"] = list(concepts)
    st["last_scene_actions"] = list(actions)
    st["last_scene_score"] = score

    store_art_artifact_memory(state, mode="scene", svg_path=path, html_path=html_path)
    update_art_hall_of_fame(state, "scene", score, path)

    return {
        "concepts": concepts,
        "actions": actions,
        "path": path,
        "score": score,
    }


def scene_svg_variant_from_concepts(concepts, seed_variant: int = 0):
    import random
    random.seed(seed_variant)

    concepts = [str(c).strip().lower() for c in concepts if str(c).strip()]
    bg = "#0b1020" if ("night" in concepts or "moon" in concepts or "star" in concepts) else "#dff1ff"
    parts = []

    moon_x = random.randint(360, 430)
    moon_y = random.randint(70, 130)
    moon_r = random.randint(38, 56)

    tree_left_x = random.randint(80, 140)
    tree_right_x = random.randint(330, 400)

    if "sun" in concepts:
        parts.append(f'<circle cx="{moon_x}" cy="{moon_y}" r="{moon_r}" fill="#ffd54a" opacity="0.95" />')
    if "moon" in concepts:
        parts.append(f'<circle cx="{moon_x}" cy="{moon_y}" r="{moon_r}" fill="#f8f3c9" opacity="0.95" />')
    if "star" in concepts or "night" in concepts or "moon" in concepts:
        parts.append(primitive_stars())
    if "mountain" in concepts:
        parts.append(primitive_mountain())
    if "river" in concepts:
        parts.append(primitive_river())
    if "ground" in concepts or "tree" in concepts or "wolf" in concepts or "mountain" in concepts:
        parts.append(primitive_ground())
    if "tree" in concepts:
        parts.append(primitive_tree(tree_left_x, 400))
        parts.append(primitive_tree(tree_right_x, 400))
    if "wolf" in concepts:
        parts.append(primitive_wolf())

    if not parts:
        parts.append('<text x="40" y="80" fill="white" font-size="22">No known scene concepts.</text>')

    return svg_wrap("\n".join(parts), 512, 512, bg=bg)


def evolve_scene_generations(state, concepts, rounds: int = 5):
    rounds = max(1, min(int(rounds), 30))
    concepts = [str(c).strip().lower() for c in concepts if str(c).strip()]

    results = []
    best = None

    for i in range(rounds):
        svg = scene_svg_variant_from_concepts(concepts, seed_variant=i + 1)
        label = "_".join(concepts[:4]) if concepts else "scene"
        path = str(next_art_path(label))
        Path(path).write_text(svg, encoding="utf-8")

        html_path = "andy_art.html"
        write_art_html_viewer(svg_path=path, html_path=html_path)

        score = guarded_art_score(state, "scene", svg)

        st = state.get("internal_state", {})
        st["last_art_mode"] = "scene"
        st["last_art_path"] = path
        st["last_art_html_path"] = html_path
        now_ts = state.get("now_ts")
        st["last_art_ts"] = now_ts() if callable(now_ts) else ""
        st["last_scene_concepts"] = list(concepts)
        st["last_scene_score"] = score

        store_art_artifact_memory(state, mode="scene", svg_path=path, html_path=html_path)
        update_art_hall_of_fame(state, "scene", score, path)
        register_lineage_entry(
            state,
            "scene",
            f"scene_v{i+1}",
            score,
            path,
        )

        item = {
            "round": i + 1,
            "label": f"scene_v{i+1}",
            "path": path,
            "score": score,
        }
        results.append(item)

        if best is None or score > best["score"]:
            best = dict(item)

    lines = [
        f"ART SCENE EVOLUTION ({rounds} rounds)",
        "",
        f"Concepts: {', '.join(concepts)}",
        "",
        "Rounds:",
    ]

    for r in results:
        lines.append(f"  {r['round']:02d}. {r['label']} | score={r['score']} | {r['path']}")

    if best:
        lines.extend([
            "",
            "BEST OVERALL:",
            f"  round={best['round']}",
            f"  label={best['label']}",
            f"  score={best['score']}",
            f"  path={best['path']}",
        ])

    text = "\n".join(lines)
    st = state.get("internal_state", {})
    st["last_scene_evolution_run"] = text
    return text

def art_gallery_text(limit: int = 12) -> str:
    art_dir = Path("art")
    if not art_dir.exists():
        return "ART GALLERY\n\nNo art directory yet."

    files = sorted(art_dir.glob("art_*.svg"))
    if not files:
        return "ART GALLERY\n\nNo saved art yet."

    lines = ["ART GALLERY", ""]
    for f in files[-limit:]:
        lines.append(f.name)

    return "\n".join(lines)


def score_art_mode(mode: str) -> float:
    mode = str(mode or "").strip().lower()
    scores = {
        "spiral": 0.72,
        "wave": 0.80,
        "random": 0.58,
        "phyllotaxis": 0.92,
        "orbit": 0.76,
        "grid": 0.62,
    }
    return scores.get(mode, 0.50)


def evolve_art(state, modes=None):
    from pathlib import Path as _Path

    parent_mode = lineage_parent_mode(state)

    builtins = set(valid_art_modes())

    if parent_mode in builtins:
        parent = candidate_from_mode(parent_mode)
        offspring_a = candidate_from_mode(parent_mode)
        offspring_b = candidate_from_mode(parent_mode)
    else:
        parent = candidate_from_discovered_mode(parent_mode)
        offspring_a = candidate_from_discovered_mode(parent_mode)
        offspring_b = candidate_from_discovered_mode(parent_mode)

    outsider = candidate_from_mode("phyllotaxis" if parent_mode != "phyllotaxis" else "orbit")

    raw_candidates = [parent, offspring_a, offspring_b, outsider]

    for discovered in discovered_mode_pool(state):
        cand = mutate_discovered_species(state, discovered)
        if cand:
            raw_candidates.append(cand)
    candidates = []

    art_dir = Path("art")
    art_dir.mkdir(exist_ok=True)

    for item in raw_candidates:
        path = str(next_art_path(item["mode"]))
        _Path(path).write_text(item["svg"], encoding="utf-8")

        html_path = "andy_art.html"
        write_art_html_viewer(svg_path=path, html_path=html_path)

        score = guarded_art_score(state, item["mode"], item["svg"])

        store_art_artifact_memory(state, mode=item["mode"], svg_path=path, html_path=html_path)

        candidates.append({
            "mode": item["mode"],
            "label": item["label"],
            "path": path,
            "score": score,
        })

    best = sorted(candidates, key=lambda x: x["score"], reverse=True)[0]

    st = state.get("internal_state", {})
    st["last_evolved_art_parent_mode"] = parent_mode
    st["last_evolved_art_mode"] = best["mode"]
    st["last_evolved_art_path"] = best["path"]
    st["last_evolved_art_score"] = best["score"]
    st["last_evolved_art_label"] = str(best.get("label", best["mode"]) or best["mode"])

    st["last_art_mode"] = best["mode"]
    st["last_art_path"] = best["path"]
    st["last_art_html_path"] = "andy_art.html"
    now_ts = state.get("now_ts")
    st["last_art_ts"] = now_ts() if callable(now_ts) else ""
    push_recent_winner_mode(state, best["mode"], limit=6)
    increment_art_win_count(state, best["mode"])
    update_art_hall_of_fame(state, best["mode"], best["score"], best["path"])
    register_lineage_entry(
        state,
        best["mode"],
        str(best.get("label", best["mode"]) or best["mode"]),
        best["score"],
        best["path"],
    )

    lines = [
        "ART EVOLUTION",
        "",
        f"Parent Mode: {parent_mode}",
        "",
        "Candidates:",
    ]
    for c in candidates:
        lines.append(f"  {c['label']}: score={c['score']} | {c['path']}")

    lines.extend([
        "",
        f"Winner: {best['mode']}",
        f"Winner Score: {best['score']}",
        f"Winner Path: {best['path']}",
    ])

    return "\n".join(lines)


def art_status_text(state) -> str:
    st = state.get("internal_state", {})
    emo = art_emotion_snapshot(state)
    recent = ", ".join(recent_winner_modes(state, limit=6))

    return "\n".join([
        "ART STATUS",
        "",
        f"Last Art Mode: {st.get('last_art_mode', '')}",
        f"Last Art Path: {st.get('last_art_path', '')}",
        f"Last Art HTML Path: {st.get('last_art_html_path', '')}",
        f"Last Art TS: {st.get('last_art_ts', '')}",
        f"Last Evolved Parent Mode: {st.get('last_evolved_art_parent_mode', '')}",
        f"Last Evolved Winner Mode: {st.get('last_evolved_art_mode', '')}",
        f"Last Evolved Winner Path: {st.get('last_evolved_art_path', '')}",
        f"Last Evolved Winner Score: {st.get('last_evolved_art_score', '')}",
        f"Recent Winner Modes: {recent}",
        f"Emotion Confidence: {emo.get('confidence', 0.0)}",
        f"Emotion Frustration: {emo.get('frustration', 0.0)}",
        f"Emotion Curiosity: {emo.get('curiosity', 0.0)}",
        f"Emotion Stability: {emo.get('stability', 0.0)}",
    ])
