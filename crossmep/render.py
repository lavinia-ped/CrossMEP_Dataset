"""SVG cross-section renderer and the interactive HTML gallery.

Drawing convention: the mounting surface is hatched (top edge for a ceiling,
left edge for a wall); round elements are pipes/conduits/round ducts, rectangles
are ducts and cable trays; dashed rings are insulation envelopes.  Only the MEP
scene is drawn -- never a support assembly.
"""
from __future__ import annotations

import json
from typing import List

from .model import MEPContext

TRADE_COLOR = {"domestic": "#2f6fed", "heating": "#e8833a", "chilled": "#0f9d8c",
               "sprinkler": "#d2434a", "electrical": "#7c5cd6", "ventilation": "#52606d"}
_HATCH = ('<defs><pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" '
          'patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="7" '
          'stroke="#cbd2d9" stroke-width="1.4"/></pattern></defs>')
_MONO = "ui-monospace,monospace"


def _draw_element(e, x0: float, y0: float, s: float, out: List[str]) -> None:
    col = TRADE_COLOR.get(e.trade, "#5a6b78")
    if e.shape == "round":
        r = max(3.0, e.width_mm * s / 2.0)
        if e.insulation_mm > 0:
            out.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="{r + max(2.0, e.insulation_mm*s):.1f}" '
                       f'fill="none" stroke="{col}" stroke-width="1" stroke-dasharray="2 2" opacity="0.55"/>')
        out.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="{r:.1f}" fill="none" stroke="{col}" stroke-width="2.3"/>')
        out.append(f'<text x="{x0:.1f}" y="{y0 + r + 11:.1f}" font-size="8.5" fill="{col}" '
                   f'text-anchor="middle" font-family="{_MONO}">{e.label}</text>')
    else:
        wpx, hpx = e.width_mm * s, e.height_mm * s
        fill = "#f4f1fa" if e.kind == "cable_tray" else "#eef1f4"
        out.append(f'<rect x="{x0-wpx/2:.1f}" y="{y0-hpx/2:.1f}" width="{wpx:.1f}" height="{hpx:.1f}" '
                   f'rx="3" fill="{fill}" stroke="{col}" stroke-width="2.3"/>')
        out.append(f'<text x="{x0:.1f}" y="{y0+3:.1f}" font-size="8.5" fill="{col}" '
                   f'text-anchor="middle" font-family="{_MONO}">{e.label}</text>')


def _footer(ctx: MEPContext) -> str:
    return (f'{len(ctx.elements)} elements · {ctx.total_load_kN:.2f} kN · '
            f'{ctx.n_levels} level(s)')


def _svg_ceiling(ctx: MEPContext, w: int) -> str:
    a_lo = min(e.position_along_mm - e.width_mm / 2 for e in ctx.elements)
    a_hi = max(e.position_along_mm + e.width_mm / 2 for e in ctx.elements)
    out_hi = max(e.position_out_mm + e.height_mm / 2 for e in ctx.elements)
    aspan = max(a_hi - a_lo, 1.0)
    padx, surf_y, topgap, padb = 22, 22, 8, 30
    s = min((w - 2 * padx) / aspan, 300.0 / max(out_hi, 1.0))
    h = int(surf_y + topgap + out_hi * s + padb)
    cx, amid = w / 2.0, (a_lo + a_hi) / 2.0
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" width="100%">', _HATCH]
    o.append(f'<rect x="0" y="0" width="{w}" height="{surf_y}" fill="url(#hatch)"/>')
    o.append(f'<line x1="0" y1="{surf_y}" x2="{w}" y2="{surf_y}" stroke="#52606d" stroke-width="2.5"/>')
    o.append(f'<text x="8" y="15" font-size="9.5" fill="#5a6b78" font-family="{_MONO}">'
             f'{ctx.surface.kind} · {ctx.surface.substrate}</text>')
    for e in ctx.elements:
        _draw_element(e, cx + (e.position_along_mm - amid) * s, surf_y + topgap + e.position_out_mm * s, s, o)
    o.append(f'<text x="{cx:.1f}" y="{h-6:.1f}" font-size="9.5" fill="#5a6b78" text-anchor="middle" '
             f'font-family="{_MONO}">{_footer(ctx)}</text>')
    o.append("</svg>")
    return "".join(o)


def _svg_wall(ctx: MEPContext, w: int) -> str:
    a_lo = min(e.position_along_mm - e.height_mm / 2 for e in ctx.elements)
    a_hi = max(e.position_along_mm + e.height_mm / 2 for e in ctx.elements)
    out_hi = max(e.position_out_mm + e.width_mm / 2 for e in ctx.elements)
    aspan = max(a_hi - a_lo, 1.0)
    wall_w, padx, topgap, padb = 16, 14, 20, 28
    s = min((w - wall_w - 2 * padx) / max(out_hi, 1.0), 300.0 / aspan)
    h = int(topgap + aspan * s + padb)
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" width="100%">', _HATCH]
    o.append(f'<rect x="0" y="0" width="{wall_w}" height="{h}" fill="url(#hatch)"/>')
    o.append(f'<line x1="{wall_w}" y1="0" x2="{wall_w}" y2="{h}" stroke="#52606d" stroke-width="2.5"/>')
    o.append(f'<text x="{wall_w+6}" y="14" font-size="9.5" fill="#5a6b78" font-family="{_MONO}">'
             f'{ctx.surface.kind} · {ctx.surface.substrate}</text>')
    for e in ctx.elements:
        _draw_element(e, wall_w + padx + e.position_out_mm * s, topgap + (e.position_along_mm - a_lo) * s, s, o)
    o.append(f'<text x="{w/2:.1f}" y="{h-6:.1f}" font-size="9.5" fill="#5a6b78" text-anchor="middle" '
             f'font-family="{_MONO}">{_footer(ctx)}</text>')
    o.append("</svg>")
    return "".join(o)


def context_svg(ctx: MEPContext, width: int = 360) -> str:
    """Standalone SVG of one context, oriented for its surface."""
    return _svg_wall(ctx, width) if ctx.surface.kind == "wall" else _svg_ceiling(ctx, width)


_GALLERY_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>MEP context dataset</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:22px;background:#f7f9fb;color:#1f2933;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
h1{font-size:18px;margin:0 0 2px}#stat{color:#5a6b78;font-size:13px;font-family:ui-monospace,Menlo,Consolas,monospace;margin:0 0 16px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#5a6b78;margin:0 0 10px}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px;margin:0 0 22px}
.chart{background:#fff;border:1px solid #d4dce2;border-radius:12px;padding:12px 14px}
.brow{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:11.5px}
.lab{width:74px;color:#3e4c59;font-family:ui-monospace,monospace;text-align:right;flex:none}
.track{flex:1;background:#eef3f6;border-radius:4px;height:14px;overflow:hidden}
.fill{display:block;height:100%;background:#0f9d8c;border-radius:4px}
.val{width:34px;color:#5a6b78;font-family:ui-monospace,monospace;flex:none}
.fbar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 8px}
.fbar .g{font-size:11px;color:#5a6b78;margin:0 4px 0 10px;text-transform:uppercase;letter-spacing:.05em}
.fbar .g:first-child{margin-left:0}
.fbar button{font:inherit;font-size:12px;padding:4px 10px;border:1px solid #d4dce2;background:#fff;border-radius:999px;cursor:pointer;color:#1f2933}
.fbar button.active{background:#16222e;color:#fff;border-color:#16222e}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;align-items:start}
.card{background:#fff;border:1px solid #d4dce2;border-radius:12px;padding:10px}
.hd{display:flex;justify-content:space-between;margin-bottom:2px}
.id{font-family:ui-monospace,monospace;font-size:12px;color:#5a6b78}.tr{font-size:11px;color:#3e4c59}
</style></head><body>
<h1>Synthetic MEP context dataset</h1>
<p id="stat"></p>
<div class="charts">
  <div class="chart"><h2>difficulty tier</h2><div id="c-tier"></div></div>
  <div class="chart"><h2>elements per context</h2><div id="c-n"></div></div>
  <div class="chart"><h2>element kinds (all)</h2><div id="c-kind"></div></div>
  <div class="chart"><h2>levels (rows)</h2><div id="c-lev"></div></div>
  <div class="chart"><h2>contexts containing trade</h2><div id="c-tr"></div></div>
  <div class="chart"><h2>total load per context (kN)</h2><div id="c-load"></div></div>
</div>
<div class="fbar">
  <span class="g">tier</span>
  <button data-g="tier" data-v="all" class="active">all</button>
  <button data-g="tier" data-v="C1">C1</button><button data-g="tier" data-v="C2">C2</button>
  <button data-g="tier" data-v="C3">C3</button><button data-g="tier" data-v="C4">C4</button>
  <button data-g="tier" data-v="C5">C5</button><button data-g="tier" data-v="C6">C6</button>
  <button data-g="tier" data-v="C7">C7</button><button data-g="tier" data-v="C8">C8</button>
  <span class="g">kind</span>
  <button data-g="kind" data-v="all" class="active">all</button>
  <button data-g="kind" data-v="pipe">pipe</button>
  <button data-g="kind" data-v="cable_tray">tray</button>
  <button data-g="kind" data-v="duct">duct</button>
  <button data-g="kind" data-v="conduit">conduit</button>
  <span class="g">trade</span>
  <button data-g="trade" data-v="all" class="active">all</button>
  <button data-g="trade" data-v="domestic">dom</button><button data-g="trade" data-v="heating">heat</button>
  <button data-g="trade" data-v="chilled">chill</button><button data-g="trade" data-v="sprinkler">sprk</button><button data-g="trade" data-v="electrical">elec</button>
  <button data-g="trade" data-v="ventilation">vent</button>
  <span class="g">surface</span>
  <button data-g="su" data-v="all" class="active">all</button>
  <button data-g="su" data-v="ceiling">ceiling</button><button data-g="su" data-v="wall">wall</button>
</div>
<div class="grid" id="grid">/*CARDS*/</div>
<script>
var DATA = /*DATA*/;
var F = {tier:"all", kind:"all", trade:"all", su:"all"};
var grid = document.getElementById('grid');
var cards = Array.prototype.slice.call(grid.children);
function matchN(n,f){ return f==="all" || (f==="7+" ? n>=7 : String(n)===f); }
function cnt(d,pred){ var k=0,i; for(i=0;i<d.length;i++){ if(pred(d[i])) k++; } return k; }
function bars(id,pairs){
  var max=1,i; for(i=0;i<pairs.length;i++){ if(pairs[i][1]>max) max=pairs[i][1]; }
  var h=""; for(i=0;i<pairs.length;i++){
    h+='<div class="brow"><span class="lab">'+pairs[i][0]+'</span><span class="track"><span class="fill" style="width:'+(100*pairs[i][1]/max)+'%"></span></span><span class="val">'+pairs[i][1]+'</span></div>';
  }
  document.getElementById(id).innerHTML=h;
}
function draw(d){
  bars('c-tier',['C1','C2','C3','C4','C5','C6','C7','C8'].map(function(t){return [t,cnt(d,function(x){return x.tier===t;})];}));
  bars('c-n',['1','2','3','4','5','6','7','8'].map(function(v){return [v,cnt(d,function(x){return matchN(x.n,v);})];}));
  var km={pipe:0,cable_tray:0,duct:0,conduit:0},i,j;
  for(i=0;i<d.length;i++){ for(j=0;j<d[i].kinds_all.length;j++){ km[d[i].kinds_all[j]]++; } }
  bars('c-kind',[['pipe',km.pipe],['tray',km.cable_tray],['duct',km.duct],['conduit',km.conduit]]);
  bars('c-lev',[1,2,3].map(function(L){return [L+' row'+(L>1?'s':''),cnt(d,function(x){return x.levels===L;})];}));
  bars('c-tr',['domestic','heating','chilled','sprinkler','electrical','ventilation'].map(function(t){return [t.slice(0,5),cnt(d,function(x){return x.trades.indexOf(t)>=0;})];}));
  var bk=[['0-0.5',0,0.5],['0.5-1',0.5,1],['1-2',1,2],['2-4',2,4],['4+',4,1e9]];
  bars('c-load',bk.map(function(b){return [b[0],cnt(d,function(x){return x.load>=b[1]&&x.load<b[2];})];}));
  var ne=0,k; for(k=0;k<d.length;k++){ ne+=d[k].n; }
  document.getElementById('stat').textContent=d.length+' contexts  \\u00b7  '+ne+' elements  \\u00b7  '+(d.length?(ne/d.length).toFixed(1):0)+' /context';
}
function ok(d){ return (F.tier==="all"||d.tier===F.tier)&&(F.kind==="all"||d.kinds.indexOf(F.kind)>=0)&&(F.trade==="all"||d.trades.indexOf(F.trade)>=0)&&(F.su==="all"||d.su===F.su); }
function apply(){
  var i; for(i=0;i<cards.length;i++){ var c=cards[i];
    var show=(F.tier==="all"||c.getAttribute('data-tier')===F.tier)
      &&(F.kind==="all"||c.getAttribute('data-kinds').split(' ').indexOf(F.kind)>=0)
      &&(F.trade==="all"||c.getAttribute('data-trades').split(' ').indexOf(F.trade)>=0)
      &&(F.su==="all"||c.getAttribute('data-su')===F.su);
    c.style.display=show?'':'none';
  }
  var vis=[]; for(i=0;i<DATA.length;i++){ if(ok(DATA[i])) vis.push(DATA[i]); }
  draw(vis);
}
var btns=document.querySelectorAll('.fbar button'),bi;
for(bi=0;bi<btns.length;bi++){ (function(b){
  b.onclick=function(){
    var g=b.getAttribute('data-g'); F[g]=b.getAttribute('data-v');
    var same=document.querySelectorAll('.fbar button[data-g="'+g+'"]'),k;
    for(k=0;k<same.length;k++){ same[k].className=(same[k]===b)?'active':''; }
    apply();
  };
})(btns[bi]); }
apply();
</script></body></html>"""


def gallery_html(contexts: List[MEPContext]) -> str:
    """Interactive gallery (filter by tier / kind / trade / surface) as one HTML string."""
    cards, data = [], []
    for ctx in contexts:
        trades = sorted({e.trade for e in ctx.elements})
        kinds = sorted({e.kind for e in ctx.elements})
        cards.append(
            f'<div class="card" data-tier="{ctx.tier}" data-trades="{" ".join(trades)}" '
            f'data-kinds="{" ".join(kinds)}" data-su="{ctx.surface.kind}">'
            f'<div class="hd"><span class="id">{ctx.context_id} · {ctx.tier}</span>'
            f'<span class="tr">{", ".join(trades)}</span></div>{context_svg(ctx)}</div>')
        data.append({"tier": ctx.tier, "n": len(ctx.elements), "levels": ctx.n_levels,
                     "trades": trades, "kinds": kinds, "kinds_all": [e.kind for e in ctx.elements],
                     "su": ctx.surface.kind, "load": round(ctx.total_load_kN, 2)})
    return (_GALLERY_TEMPLATE.replace("/*CARDS*/", "".join(cards))
            .replace("/*DATA*/", json.dumps(data)))


def render_gallery_html(contexts: List[MEPContext], path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(gallery_html(contexts))
    return path
