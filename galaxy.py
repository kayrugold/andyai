# galaxy.py - Level 3 Visualizer for AndyAI (fixed + self-contained)
import json
import math
from string import Template
from typing import Any, Dict, List


def _cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity (self-contained; avoids recall.py import mismatches)."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = 0.0
    ma = 0.0
    mb = 0.0
    for i in range(n):
        av = float(a[i])
        bv = float(b[i])
        dot += av * bv
        ma += av * av
        mb += bv * bv
    denom = math.sqrt(ma) * math.sqrt(mb)
    return float(dot / denom) if denom else 0.0


def write_galaxy_html(db: Any, out_path: str) -> None:
    """
    Accepts either:
      - db as dict: {"entries":[{id,text,embedding,...}, ...]}
      - db as list: [{id,text,embedding,...}, ...]
    """
    if isinstance(db, dict):
        entries = db.get("entries", [])
    elif isinstance(db, list):
        entries = db
    else:
        entries = []

    # 1) Prepare nodes
    nodes = []
    for e in entries:
        text = str(e.get("text", "") or "")
        nodes.append(
            {
                "id": str(e.get("id", "")),
                "label": (text[:45] + "...") if len(text) > 45 else text,
                "text": text,
                "tags": e.get("tags", []),
            }
        )

    # 2) Generate edges (semantic relationships)
    links = []
    threshold = 0.75
    for i, a in enumerate(entries):
        for j, b in enumerate(entries):
            if i >= j:
                continue
            score = _cosine(a.get("embedding", []), b.get("embedding", []))
            if score > threshold:
                links.append(
                    {
                        "source": str(a.get("id", "")),
                        "target": str(b.get("id", "")),
                        "weight": round(float(score), 4),
                    }
                )

    data_json = json.dumps({"nodes": nodes, "links": links})

    # 3) Mobile-first HTML template
    html_template = Template(
        r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <title>AndyAI Galaxy</title>
  <style>
    body { margin: 0; background: #050612; color: #e7e7ff; font-family: monospace; overflow: hidden; height: 100vh; }
    header { padding: 10px; border-bottom: 1px solid #222; background: #0a0b1e; font-size: 14px; }
    #wrap { display: flex; flex-direction: column; height: calc(100vh - 45px); }
    #left { flex: 1; position: relative; }
    #right { height: 180px; border-top: 1px solid #222; padding: 12px; overflow: auto; background: #0a0b1e; }
    canvas { display: block; width: 100%; height: 100%; touch-action: none; }
    pre { white-space: pre-wrap; font-size: 12px; color: #acf; }
    .hint { font-size: 10px; opacity: 0.6; }
  </style>
</head>
<body>
<header><strong>AndyAI Galaxy</strong> <span class="hint">Pinch to Zoom | Drag to Move | Tap to Read</span></header>
<div id="wrap">
  <div id="left"><canvas id="c"></canvas></div>
  <aside id="right">
    <div id="meta">Select a memory node...</div>
    <pre id="text"></pre>
  </aside>
</div>

<script>
(function(){
  const DATA = $DATA_JSON;

  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d');

  function fit() {
    const r = canvas.getBoundingClientRect();
    const dpr = (window.devicePixelRatio || 1);
    canvas.width = r.width * dpr;
    canvas.height = r.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', fit);
  fit();

  // Basic physics layout
  const nodes = DATA.nodes.map((n, idx) => ({
    ...n,
    x: (Math.random()*canvas.clientWidth),
    y: (Math.random()*canvas.clientHeight),
    vx: 0, vy: 0,
    r: 10 + Math.min(20, (n.text||"").length / 12)
  }));

  const links = DATA.links.map(l => ({
    ...l,
    a: nodes.find(n => n.id === l.source),
    b: nodes.find(n => n.id === l.target)
  })).filter(l => l.a && l.b);

  let panX = 0, panY = 0;
  let zoom = 1;

  // Touch/mouse state
  let dragging = false;
  let lastX = 0, lastY = 0;

  function worldToScreen(x,y){
    return { x: (x + panX)*zoom, y: (y + panY)*zoom };
  }
  function screenToWorld(x,y){
    return { x: (x/zoom) - panX, y: (y/zoom) - panY };
  }

  function draw(){
    ctx.clearRect(0,0,canvas.clientWidth, canvas.clientHeight);

    // edges
    for(const l of links){
      const A = worldToScreen(l.a.x, l.a.y);
      const B = worldToScreen(l.b.x, l.b.y);
      ctx.globalAlpha = Math.max(0.15, Math.min(0.75, l.weight || 0.3));
      ctx.beginPath();
      ctx.moveTo(A.x, A.y);
      ctx.lineTo(B.x, B.y);
      ctx.strokeStyle = "#3b82f6";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // nodes
    for(const n of nodes){
      const S = worldToScreen(n.x, n.y);
      ctx.beginPath();
      ctx.arc(S.x, S.y, n.r*zoom*0.35, 0, Math.PI*2);
      ctx.fillStyle = "#22d3ee";
      ctx.fill();
      ctx.strokeStyle = "#0ea5e9";
      ctx.stroke();

      // label
      ctx.fillStyle = "#e7e7ff";
      ctx.font = `${Math.max(10, 12*zoom)}px monospace`;
      ctx.fillText(n.label || "", S.x + 10, S.y - 10);
    }
  }

  function stepPhysics(){
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;

    // repel
    for(let i=0;i<nodes.length;i++){
      for(let j=i+1;j<nodes.length;j++){
        const a = nodes[i], b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const d2 = dx*dx + dy*dy + 0.01;
        const f = 80 / d2;
        a.vx += (dx/Math.sqrt(d2)) * f;
        a.vy += (dy/Math.sqrt(d2)) * f;
        b.vx -= (dx/Math.sqrt(d2)) * f;
        b.vy -= (dy/Math.sqrt(d2)) * f;
      }
    }

    // springs
    for(const l of links){
      const a = l.a, b = l.b;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx*dx + dy*dy) + 0.001;
      const target = 140 / (l.weight || 0.3);
      const k = 0.01;
      const f = (dist - target) * k;
      a.vx += (dx/dist) * f;
      a.vy += (dy/dist) * f;
      b.vx -= (dx/dist) * f;
      b.vy -= (dy/dist) * f;
    }

    // integrate
    for(const n of nodes){
      n.vx *= 0.85;
      n.vy *= 0.85;
      n.x += n.vx;
      n.y += n.vy;

      // soft bounds
      n.x = Math.max(-w, Math.min(2*w, n.x));
      n.y = Math.max(-h, Math.min(2*h, n.y));
    }
  }

  // hit test
  function pickNode(screenX, screenY){
    const p = screenToWorld(screenX, screenY);
    let best = null;
    let bestD = 1e9;
    for(const n of nodes){
      const dx = p.x - n.x;
      const dy = p.y - n.y;
      const d = Math.sqrt(dx*dx + dy*dy);
      if(d < (n.r*0.8) && d < bestD){
        bestD = d;
        best = n;
      }
    }
    return best;
  }

  function showNode(n){
    document.getElementById('meta').textContent = `ID: ${n.id} | Tags: ${(n.tags||[]).join(", ")}`;
    document.getElementById('text').textContent = n.text || "";
  }

  // pointer controls
  canvas.addEventListener('pointerdown', (ev)=>{
    canvas.setPointerCapture(ev.pointerId);
    dragging = true;
    lastX = ev.clientX;
    lastY = ev.clientY;
  });

  canvas.addEventListener('pointermove', (ev)=>{
    if(!dragging) return;
    const dx = ev.clientX - lastX;
    const dy = ev.clientY - lastY;
    lastX = ev.clientX;
    lastY = ev.clientY;

    panX += dx / zoom;
    panY += dy / zoom;
  });

  canvas.addEventListener('pointerup', (ev)=>{
    dragging = false;
    const n = pickNode(ev.clientX, ev.clientY);
    if(n) showNode(n);
  });

  // wheel zoom (desktop)
  canvas.addEventListener('wheel', (ev)=>{
    ev.preventDefault();
    const factor = ev.deltaY > 0 ? 0.95 : 1.05;
    zoom = Math.max(0.25, Math.min(3.0, zoom * factor));
  }, {passive:false});

  function loop(){
    stepPhysics();
    draw();
    requestAnimationFrame(loop);
  }
  loop();
})();
</script>
</body>
</html>
"""
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_template.safe_substitute(DATA_JSON=data_json))