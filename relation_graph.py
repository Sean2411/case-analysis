"""生成可单独打开的法律关系图页面，版式对齐交付用的法律关系图。"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass

FENCE_RE = re.compile(r"```relation-graph\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

ROLES = ("client", "defendant", "object", "third")
KINDS = {"money", "breach", "procedure", "contract"}

ROLE_STYLE = {
    "client": ("#1f4e79", "#eef4fb", "3px", "一方当事人"),
    "defendant": ("#b9770e", "#fff", "2px", "相对方"),
    "object": ("#2e8b57", "#eff8f1", "2px", "标的"),
    "third": ("#7f8c8d", "#fff", "2px", "第三方"),
}
EDGE_STYLE = {
    "money": ("#2e8b57", "dashed", "资金流向"),
    "breach": ("#d0342c", "dashed", "违约或请求"),
    "procedure": ("#8a8f98", "dotted", "程序事项"),
    "contract": ("#2f6db5", "solid", "合同关系"),
}

CARD_WIDTH = 240
GRAPH_WIDTH = 1180

_DRAW_SCRIPT = r"""
const EDGES = __EDGES__;
const STYLE = {"contract":["#2f6db5","solid",2.2],"money":["#2e8b57","dashed",2.4],"breach":["#d0342c","dashed",2.4],"procedure":["#8a8f98","dotted",2.2]};
const g = document.querySelector('.graph');
const svg = g.querySelector('.edges');
const NS = 'http://www.w3.org/2000/svg';
const base = g.getBoundingClientRect();
const defs = document.createElementNS(NS,'defs');
svg.appendChild(defs);
for (const [k,[c]] of Object.entries(STYLE)) {
  const m = document.createElementNS(NS,'marker');
  m.setAttribute('id','m-'+k);
  m.setAttribute('viewBox','0 0 10 10');
  m.setAttribute('refX','9');
  m.setAttribute('refY','5');
  m.setAttribute('markerUnits','userSpaceOnUse');
  m.setAttribute('markerWidth','13');
  m.setAttribute('markerHeight','13');
  m.setAttribute('orient','auto-start-reverse');
  const p = document.createElementNS(NS,'path');
  p.setAttribute('d','M0,0 L10,5 L0,10 z');
  p.setAttribute('fill',c);
  m.appendChild(p);
  defs.appendChild(m);
}
function box(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {id, x:r.left-base.left+r.width/2, y:r.top-base.top+r.height/2, w:r.width/2+8, h:r.height/2+8};
}
function edgePoint(b, tx, ty) {
  const dx = tx-b.x, dy = ty-b.y;
  if (!dx && !dy) return [b.x, b.y];
  const t = Math.min(b.w/Math.abs(dx||1e-9), b.h/Math.abs(dy||1e-9));
  return [b.x+dx*t, b.y+dy*t];
}
const pairCounts = {};
EDGES.forEach(e => { const k=[e.from,e.to].sort().join('>'); pairCounts[k]=(pairCounts[k]||0)+1; });
const pairSeen = {};
const labelEls = [];
for (const e of EDGES) {
  const A = box(e.from), B = box(e.to);
  if (!A || !B) continue;
  const [c,dash,w] = STYLE[e.kind] || STYLE.contract;
  const k = [e.from,e.to].sort().join('>');
  const idx = pairSeen[k]||0; pairSeen[k]=idx+1;
  const cnt = pairCounts[k];
  const sign = e.from < e.to ? 1 : -1;
  let bend = 36 * sign;
  if (cnt === 2) bend = (idx===0?78:-78)*sign;
  else if (cnt > 2) bend = (idx-(cnt-1)/2)*68*sign;
  const mx=(A.x+B.x)/2, my=(A.y+B.y)/2, L=Math.hypot(B.x-A.x,B.y-A.y)||1;
  const nx=-(B.y-A.y)/L, ny=(B.x-A.x)/L;
  const cx=mx+nx*bend, cy=my+ny*bend;
  const P0=edgePoint(A,cx,cy), P2=edgePoint(B,cx,cy);
  const path=document.createElementNS(NS,'path');
  path.setAttribute('d',`M${P0[0]},${P0[1]} Q${cx},${cy} ${P2[0]},${P2[1]}`);
  path.setAttribute('fill','none');
  path.setAttribute('stroke',c);
  path.setAttribute('stroke-width',w);
  if (dash==='dashed') path.setAttribute('stroke-dasharray','8 5');
  if (dash==='dotted') path.setAttribute('stroke-dasharray','2 5');
  path.setAttribute('stroke-linecap','round');
  path.setAttribute('marker-end','url(#m-'+(STYLE[e.kind]?e.kind:'contract')+')');
  svg.appendChild(path);
  if (e.label) {
    const d=document.createElement('div');
    d.className='elabel';
    d.style.color = c==='#8a8f98' ? '#555' : c;
    String(e.label).split('\n').forEach((line,i) => {
      if (i) d.appendChild(document.createElement('br'));
      d.appendChild(document.createTextNode(line));
    });
    g.appendChild(d);
    d.style.left=(0.25*P0[0]+0.5*cx+0.25*P2[0])+'px';
    d.style.top=(0.25*P0[1]+0.5*cy+0.25*P2[1])+'px';
    labelEls.push(d);
  }
}
const nodeRects=[...g.querySelectorAll('.node')].map(el => {
  const r=el.getBoundingClientRect();
  return {left:r.left-base.left-4, right:r.right-base.left+4, top:r.top-base.top-4, bottom:r.bottom-base.top+4};
});
function overlaps(el, rect) {
  const r=el.getBoundingClientRect();
  const a={left:r.left-base.left, right:r.right-base.left, top:r.top-base.top, bottom:r.bottom-base.top};
  const ox=Math.min(a.right,rect.right)-Math.max(a.left,rect.left);
  const oy=Math.min(a.bottom,rect.bottom)-Math.max(a.top,rect.top);
  return ox>2 && oy>2 ? oy : 0;
}
for (let pass=0; pass<8; pass++) {
  for (const el of labelEls) {
    for (const nr of nodeRects) {
      const hit=overlaps(el, nr);
      if (hit) el.style.top=(parseFloat(el.style.top)-hit-8)+'px';
    }
  }
}
"""


@dataclass(frozen=True)
class GraphNode:
    id: str
    name: str
    role: str
    subtitle: str
    detail: str
    source: str


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: str
    label: str


@dataclass
class CourtBlock:
    title: str
    lines: list[str]
    source: str


@dataclass
class EntityRow:
    name: str
    role: str
    org: str
    gender: str
    birth: str
    ethnicity: str
    id_no: str
    address: str
    phone: str
    license_no: str
    source: str


def parse_relation_graph(text: str) -> dict | None:
    """从模型输出里取出关系图。格式不对就返回 None，界面只显示文字。"""

    match = FENCE_RE.search(text or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    nodes = _nodes(data.get("nodes"))
    if not nodes:
        return None
    edges = _edges(data.get("edges"), {node.id for node in nodes})
    return {
        "title": _clip(data.get("title"), 80),
        "nodes": nodes,
        "edges": edges,
        "court": _court(data.get("court")),
        "entities": _entities(data.get("entities")),
    }


def strip_relation_fence(text: str) -> str:
    cleaned = FENCE_RE.sub("", text or "")
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def render_relation_html(graph: dict) -> tuple[str, int]:
    """返回可单独用浏览器打开的完整页面，以及建议展示高度。"""

    nodes: list[GraphNode] = graph["nodes"]
    edges: list[GraphEdge] = graph["edges"]
    placed, graph_height = _layout(nodes)
    dom_ids = {node.id: f"n{index}" for index, node in enumerate(nodes)}
    cards = [_card_html(node, placed[node], dom_ids[node.id]) for node in nodes]
    legend = _legend_html(edges)
    court_html = _court_html(graph.get("court"))
    entities = list(graph.get("entities") or []) or _entities_from_nodes(nodes)
    table_html = _entity_table(entities)
    title = graph.get("title") or ""
    heading = "法律关系图" + (f" · {html.escape(title)}" if title else "")
    edge_payload = [
        {
            "from": dom_ids[edge.source],
            "to": dom_ids[edge.target],
            "kind": edge.kind,
            "label": edge.label,
        }
        for edge in edges
        if edge.source in dom_ids and edge.target in dom_ids
    ]
    blob = json.dumps(edge_payload, ensure_ascii=False).replace("<", "\\u003c")
    page = _PAGE.replace("__HEADING__", heading)
    page = page.replace("__LEGEND__", legend)
    page = page.replace("__GRAPH_W__", str(GRAPH_WIDTH))
    page = page.replace("__GRAPH_H__", str(graph_height))
    page = page.replace("__CARDS__", "".join(cards))
    page = page.replace("__COURT__", court_html)
    page = page.replace("__TABLE__", table_html)
    page = page.replace("__EDGES__", blob)
    table_height = 96 + 46 * max(len(entities), 1)
    court_extra = 0 if court_html else 0
    page_height = 150 + graph_height + table_height + court_extra
    return page, page_height


def _nodes(raw: object) -> list[GraphNode]:
    if not isinstance(raw, list):
        return []
    nodes: list[GraphNode] = []
    seen: set[str] = set()
    for item in raw[:8]:
        if not isinstance(item, dict):
            continue
        name = _clip(item.get("name"), 80)
        node_id = _clip(item.get("id") or name, 40)
        if not name or not node_id or node_id in seen:
            continue
        role = str(item.get("role") or "third").strip()
        if role not in ROLES:
            role = "third"
        seen.add(node_id)
        nodes.append(
            GraphNode(
                id=node_id,
                name=name,
                role=role,
                subtitle=_clip(item.get("subtitle"), 100),
                detail=_clip(item.get("detail"), 140),
                source=_clip(item.get("source"), 80),
            )
        )
    return nodes


def _edges(raw: object, node_ids: set[str]) -> list[GraphEdge]:
    if not isinstance(raw, list):
        return []
    edges: list[GraphEdge] = []
    for item in raw[:12]:
        if not isinstance(item, dict):
            continue
        source = str(item.get("from") or "").strip()
        target = str(item.get("to") or "").strip()
        if source not in node_ids or target not in node_ids or source == target:
            continue
        kind = str(item.get("kind") or "contract").strip()
        if kind not in KINDS:
            kind = "contract"
        label = str(item.get("label") or "").replace("\\n", "\n").strip()[:180]
        edges.append(GraphEdge(source, target, kind, label))
    return edges


def _court(raw: object) -> CourtBlock | None:
    if not isinstance(raw, dict):
        return None
    lines_raw = raw.get("lines")
    lines: list[str] = []
    if isinstance(lines_raw, list):
        lines = [_clip(item, 180) for item in lines_raw if _clip(item, 180)]
    elif isinstance(lines_raw, str) and lines_raw.strip():
        lines = [_clip(lines_raw, 180)]
    lines = lines[:8]
    if not lines:
        return None
    title = _clip(raw.get("title"), 80) or "法院认定"
    return CourtBlock(title=title, lines=lines, source=_clip(raw.get("source"), 80))


def _entities(raw: object) -> list[EntityRow]:
    if not isinstance(raw, list):
        return []
    rows: list[EntityRow] = []
    for item in raw[:24]:
        if not isinstance(item, dict):
            continue
        name = _clip(item.get("name"), 80)
        if not name:
            continue
        rows.append(
            EntityRow(
                name=name,
                role=_clip(item.get("role"), 80),
                org=_clip(item.get("org"), 80),
                gender=_clip(item.get("gender"), 8),
                birth=_clip(item.get("birth"), 20),
                ethnicity=_clip(item.get("ethnicity"), 16),
                id_no=_clip(item.get("id_no"), 32),
                address=_clip(item.get("address"), 80),
                phone=_clip(item.get("phone"), 24),
                license_no=_clip(item.get("license_no"), 32),
                source=_clip(item.get("source"), 80),
            )
        )
    return rows


def _entities_from_nodes(nodes: list[GraphNode]) -> list[EntityRow]:
    return [
        EntityRow(
            name=node.name,
            role=node.subtitle,
            org="",
            gender="",
            birth="",
            ethnicity="",
            id_no="",
            address="",
            phone="",
            license_no="",
            source=node.source,
        )
        for node in nodes
    ]


def _clip(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _card_height(node: GraphNode) -> int:
    lines = 1
    for text in (node.subtitle, node.detail):
        if text:
            lines += max(1, (len(text) + 17) // 18)
    if node.source:
        lines += 1
    return 32 + lines * 22


def _layout(nodes: list[GraphNode]) -> tuple[dict[GraphNode, tuple[int, int, int]], int]:
    """第三方在左，相对方在上，一方当事人在右，标的在下方。"""

    groups = {role: [node for node in nodes if node.role == role] for role in ROLES}
    present = [role for role in ROLES if groups[role]]
    placed: dict[GraphNode, tuple[int, int, int]] = {}
    if len(present) <= 1:
        members = groups[present[0]] if present else []
        cols = 1 if len(members) <= 1 else min(3, len(members))
        cursor_y = [48] * cols
        for index, node in enumerate(members):
            col = index % cols
            height = _card_height(node)
            x = GRAPH_WIDTH // 2 if cols == 1 else 220 + col * 320
            y = cursor_y[col] + height / 2
            placed[node] = (x, int(y), height)
            cursor_y[col] += height + 48
        bottom = max(cursor_y) if cursor_y else 480
        return placed, max(520, int(bottom + 72))

    def place(members: list[GraphNode], x: int, top: int) -> int:
        y = top
        for node in members:
            height = _card_height(node)
            placed[node] = (x, int(y + height / 2), height)
            y += height + 78
        return y

    left_bottom = place(groups["third"], 230, 48)
    defendant_x = 980 if not groups["client"] else 700
    defendant_bottom = place(groups["defendant"], defendant_x, 40)
    if groups["client"] and defendant_x > 900:
        client_top = defendant_bottom + 28
    elif groups["defendant"]:
        client_top = 310
    else:
        client_top = 48
    client_bottom = place(groups["client"], 980, client_top)
    content_bottom = max(left_bottom, defendant_bottom, client_bottom)
    object_bottom = place(groups["object"], 560, content_bottom + 36)
    return placed, max(690, int(max(content_bottom, object_bottom) + 64))


def _card_html(node: GraphNode, box: tuple[int, int, int], dom_id: str) -> str:
    x, y, _height = box
    color, _background, _border_width, badge = ROLE_STYLE[node.role]
    lines = []
    if node.subtitle:
        lines.append(f'<div class="nl">{html.escape(node.subtitle)}</div>')
    if node.detail:
        lines.append(f'<div class="nl">{html.escape(node.detail)}</div>')
    if node.source:
        lines.append(f'<div class="nf">见于 {html.escape(node.source)}</div>')
    badge_html = f'<span class="badge">{html.escape(badge)}</span>' if node.role == "client" else ""
    return (
        f'<div class="node {node.role}" id="{dom_id}" style="left:{x}px;top:{y}px;border-color:{color}">'
        f'<div class="nt" style="color:{color}">{html.escape(node.name)}{badge_html}</div>'
        f'{"".join(lines)}</div>'
    )


def _legend_html(edges: list[GraphEdge]) -> str:
    present = [kind for kind in EDGE_STYLE if any(edge.kind == kind for edge in edges)] or list(EDGE_STYLE)
    parts = []
    for kind in present:
        color, dash, label = EDGE_STYLE[kind]
        dash_attr = ' stroke-dasharray="6 4"' if dash == "dashed" else ""
        if dash == "dotted":
            dash_attr = ' stroke-dasharray="2 4"'
        parts.append(
            f'<span class="lg"><svg width="34" height="10"><line x1="0" y1="5" x2="34" y2="5" '
            f'stroke="{color}" stroke-width="2.4"{dash_attr}/></svg>{html.escape(label)}</span>'
        )
    return "".join(parts)


def _court_html(court: CourtBlock | None) -> str:
    if court is None:
        return ""
    lines = "".join(f'<div class="cl">{html.escape(line)}</div>' for line in court.lines)
    source = f'<div class="cf">见于 {html.escape(court.source)}</div>' if court.source else ""
    return f'<div class="court"><div class="ct">{html.escape(court.title)}</div>{lines}{source}</div>'


def _entity_table(rows: list[EntityRow]) -> str:
    body = []
    seen_org: set[str] = set()
    for row in rows:
        if row.org and row.org not in seen_org:
            seen_org.add(row.org)
            body.append(
                '<tr class="eh"><td colspan="10"><b class="en">'
                + html.escape(row.org)
                + "</b></td></tr>"
            )
        body.append(
            "<tr class=\"pr\">"
            f"<td><b>{html.escape(row.name)}</b></td>"
            f"<td class=\"sub2\">{_blank(row.role)}</td>"
            f"<td class=\"nw\">{_blank(row.gender)}</td>"
            f"<td class=\"nw\">{_blank(row.birth)}</td>"
            f"<td class=\"nw\">{_blank(row.ethnicity)}</td>"
            f"<td class=\"nw mono\">{_blank(row.id_no)}</td>"
            f"<td>{_blank(row.address)}</td>"
            f"<td class=\"nw mono\">{_blank(row.phone)}</td>"
            f"<td class=\"nw mono\">{_blank(row.license_no)}</td>"
            f"<td class=\"nf2\">{_blank(row.source)}</td>"
            "</tr>"
        )
    return (
        '<div class="panel"><div class="ph"><h2>主体和人员</h2></div>'
        '<p class="note">只列出材料写明的名称和身份。材料没有记载的项目留空，不补充。</p>'
        '<table class="ent"><colgroup>'
        '<col style="width:120px"><col style="width:180px"><col style="width:52px">'
        '<col style="width:110px"><col style="width:64px"><col style="width:180px">'
        "<col><col style=\"width:120px\"><col style=\"width:140px\"><col style=\"width:140px\">"
        "</colgroup><tr><th>姓名</th><th>在本案中的身份</th><th>性别</th><th>出生日期</th>"
        "<th>民族</th><th>公民身份号码</th><th>住址</th><th>电话</th><th>执业证号</th><th>见于</th></tr>"
        + "".join(body)
        + "</table></div>"
    )


def _blank(value: str) -> str:
    text = value.strip()
    if not text:
        return '<span class="na">—</span>'
    return html.escape(text)


_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>法律关系图</title><style>
*{box-sizing:border-box}
body{margin:0;background:#f4f6f9;font-family:"PingFang SC","Noto Sans CJK SC","Noto Sans SC","Microsoft YaHei",sans-serif;color:#222;font-size:15px}
.wrap{width:1660px;padding:28px 32px}
h1{font-size:28px;margin:0 0 4px}
.sub{color:#666;margin-bottom:18px}
.panel{background:#fff;border-radius:16px;box-shadow:0 2px 10px rgba(0,0,0,.06);padding:20px 22px;margin-bottom:22px}
.ph{display:flex;align-items:baseline;gap:18px;margin-bottom:10px;flex-wrap:wrap}
.ph h2{font-size:20px;margin:0}
.lg{display:inline-flex;align-items:center;gap:6px;margin-right:14px;color:#555;font-size:13px}
.rel{display:flex;gap:22px;align-items:flex-start}
.graph{position:relative;width:__GRAPH_W__px;height:__GRAPH_H__px;flex:none}
.edges{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible}
.node{position:absolute;transform:translate(-50%,-50%);width:240px;background:#fff;border:2px solid;border-radius:12px;padding:9px 12px;box-shadow:0 2px 6px rgba(0,0,0,.08);z-index:2}
.node.client{background:#eef4fb;border-width:3px}
.node.object{background:#eff8f1}
.nt{font-weight:700;font-size:16px;line-height:1.35}
.nl{font-size:13px;color:#444;line-height:1.45}
.nf{font-size:12px;color:#1f4e79;margin-top:3px}
.badge{display:inline-block;white-space:nowrap;background:#1f4e79;color:#fff;border-radius:9px;font-size:12px;padding:1px 8px;margin-left:8px;vertical-align:2px}
.elabel{position:absolute;transform:translate(-50%,-50%);background:rgba(255,255,255,.94);border-radius:6px;padding:2px 7px;font-size:12.5px;line-height:1.4;text-align:center;z-index:3;max-width:280px}
.court{width:360px;flex:none;background:#fff8e1;border:1px solid #e6c65c;border-radius:12px;padding:14px 16px}
.ct{font-weight:700;margin-bottom:6px}
.cl{font-size:13.5px;line-height:1.6}
.cf{font-size:12px;color:#1f4e79;margin-top:6px}
.note{color:#555;font-size:14px;margin:0 0 12px;line-height:1.6}
.ent{width:1616px;border-collapse:collapse;font-size:13px;table-layout:fixed}
.ent th{background:#2b3440;color:#fff;font-weight:600;padding:8px 10px;text-align:left}
.ent td{border-bottom:1px solid #e3e6eb;padding:8px 10px;vertical-align:top;line-height:1.5;word-break:break-all}
.ent .sub2{color:#777;font-size:12px}
.ent .na{color:#aaa}
.ent .nw{white-space:nowrap;word-break:keep-all}
.ent .mono{font-family:"Noto Sans Mono CJK SC","SFMono-Regular",ui-monospace,monospace}
.ent tr.eh td{background:#eef2f7;border-top:2px solid #b8c4d3;padding:9px 10px}
.ent .en{font-size:14.5px;color:#1f2d3d}
.ent tr.pr td{padding:6px 10px}
.ent .nf2{color:#1f4e79;font-size:12.5px}
</style></head><body><div class="wrap">
<h1>__HEADING__</h1>
<div class="sub">当事人之间的法律关系。卡片、连线和表格只使用材料写明的内容。</div>
<div class="panel"><div class="ph"><h2>法律关系</h2><div>__LEGEND__</div></div>
<div class="rel"><div class="graph" style="height:__GRAPH_H__px"><svg class="edges"></svg>__CARDS__</div>__COURT__</div>
</div>
__TABLE__
</div>
<script>
__DRAW__
</script>
</body></html>
""".replace("__DRAW__", _DRAW_SCRIPT)
