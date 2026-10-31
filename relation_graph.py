"""把人物关系渲染成卡片式法律关系图，版式参考交付用的法律关系图。"""

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
    "money": ("#2e8b57", "8 5", "资金流向"),
    "breach": ("#d0342c", "8 5", "违约或请求"),
    "procedure": ("#8a8f98", "2 5", "程序事项"),
    "contract": ("#2f6db5", "", "合同关系"),
}

CARD_WIDTH = 240
GRAPH_WIDTH = 1040


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
    return {"nodes": nodes, "edges": edges}


def strip_relation_fence(text: str) -> str:
    cleaned = FENCE_RE.sub("", text or "")
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def render_relation_html(graph: dict) -> tuple[str, int]:
    """返回完整 HTML 和建议的展示高度。"""

    nodes: list[GraphNode] = graph["nodes"]
    edges: list[GraphEdge] = graph["edges"]
    placed, height = _layout(nodes)
    cards = [_card_html(node, box) for node, box in placed.items()]
    svg, labels = _edges_svg(placed, edges)
    legend = "".join(
        f'<span class="lg"><svg width="34" height="10"><line x1="0" y1="5" x2="34" y2="5" '
        f'stroke="{color}" stroke-width="2.4" {_dash_attr(dash)}/></svg>{html.escape(label)}</span>'
        for color, dash, label in EDGE_STYLE.values()
    )
    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f4f6f9;font-family:"PingFang SC","Noto Sans CJK SC","Noto Sans SC","Microsoft YaHei",sans-serif;color:#222}}
.panel{{background:#fff;border-radius:16px;box-shadow:0 2px 10px rgba(0,0,0,.06);padding:18px 20px 22px}}
.ph h2{{font-size:20px;margin:0}}
.sub{{color:#666;font-size:13px;margin:4px 0 8px}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 0 2px}}
.lg{{display:inline-flex;align-items:center;gap:6px;color:#555;font-size:13px}}
.graph{{position:relative;height:{height}px;width:{GRAPH_WIDTH}px}}
.edges{{position:absolute;inset:0;width:100%;height:100%;overflow:visible}}
.node{{position:absolute;transform:translate(-50%,-50%);width:{CARD_WIDTH}px;background:#fff;border:2px solid;border-radius:12px;
 padding:9px 12px;box-shadow:0 2px 6px rgba(0,0,0,.08);z-index:2}}
.nt{{font-weight:700;font-size:16px;line-height:1.35}}
.badge{{display:inline-block;white-space:nowrap;background:#1f4e79;color:#fff;border-radius:9px;font-size:12px;padding:1px 8px;margin-left:8px;vertical-align:2px}}
.nl{{font-size:13px;color:#444;line-height:1.45;margin-top:2px}}
.nf{{font-size:12px;color:#1f4e79;margin-top:3px}}
.elabel{{position:absolute;transform:translate(-50%,-50%);max-width:210px;background:rgba(255,255,255,.94);
 border-radius:6px;padding:2px 7px;font-size:12.5px;line-height:1.4;text-align:center;z-index:3}}
</style></head><body><div class="panel">
<div class="ph"><h2>法律关系</h2><div class="legend">{legend}</div></div>
<p class="sub">卡片和连线只标出材料写明的主体和关系。</p>
<div class="graph">{svg}{"".join(cards)}{"".join(labels)}</div>
</div></body></html>"""
    return page, height + 140


def _nodes(raw: object) -> list[GraphNode]:
    if not isinstance(raw, list):
        return []
    nodes: list[GraphNode] = []
    seen: set[str] = set()
    for item in raw[:8]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        node_id = str(item.get("id") or name).strip()
        if not name or not node_id or node_id in seen:
            continue
        role = str(item.get("role") or "third").strip()
        if role not in ROLES:
            role = "third"
        seen.add(node_id)
        nodes.append(
            GraphNode(
                id=node_id,
                name=name[:40],
                role=role,
                subtitle=str(item.get("subtitle") or "").strip()[:80],
                detail=str(item.get("detail") or "").strip()[:80],
                source=str(item.get("source") or "").strip()[:80],
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
        edges.append(GraphEdge(source, target, kind, str(item.get("label") or "").strip()[:90]))
    return edges


def _card_height(node: GraphNode) -> int:
    extra = sum(1 for text in (node.subtitle, node.detail, node.source) if text)
    return 48 + extra * 20


def _layout(nodes: list[GraphNode]) -> tuple[dict[GraphNode, tuple[int, int, int]], int]:
    """按身份分栏，版式接近参考图：第三方在左，相对方在上，当事人在右，标的在下。"""

    groups = {role: [node for node in nodes if node.role == role] for role in ROLES}
    present = [role for role in ROLES if groups[role]]
    placed: dict[GraphNode, tuple[int, int, int]] = {}
    if len(present) <= 1:
        members = groups[present[0]] if present else []
        cols = 1 if len(members) <= 1 else min(3, len(members))
        cursor_y = [36] * cols
        for index, node in enumerate(members):
            col = index % cols
            height = _card_height(node)
            x = GRAPH_WIDTH // 2 if cols == 1 else 200 + col * 300
            y = cursor_y[col] + height / 2
            placed[node] = (x, int(y), height)
            cursor_y[col] += height + 36
        bottom = max(cursor_y) if cursor_y else 420
        return placed, max(460, int(bottom + 64))

    def place(members: list[GraphNode], x: int, top: int, stagger: int = 0) -> int:
        y = top
        for index, node in enumerate(members):
            height = _card_height(node)
            placed[node] = (x + (stagger if index % 2 else 0), int(y + height / 2), height)
            y += height + 56
        return y

    left_bottom = place(groups["third"], 190, 36)
    defendant_x = 860 if not groups["client"] else 620
    defendant_bottom = place(groups["defendant"], defendant_x, 28)
    if groups["client"] and defendant_x > 760:
        client_top = defendant_bottom + 12
    elif groups["defendant"]:
        client_top = 250
    else:
        client_top = 36
    client_bottom = place(groups["client"], 860, client_top)
    content_bottom = max(left_bottom, defendant_bottom, client_bottom)
    object_x = 480 if (groups["third"] or groups["client"] or groups["defendant"]) else 420
    object_bottom = place(groups["object"], object_x, content_bottom + 16)
    return placed, max(480, int(max(content_bottom, object_bottom) + 72))


def _card_html(node: GraphNode, box: tuple[int, int, int]) -> str:
    x, y, _height = box
    color, background, border_width, badge = ROLE_STYLE[node.role]
    lines = []
    if node.subtitle:
        lines.append(f'<div class="nl">{html.escape(node.subtitle)}</div>')
    if node.detail:
        lines.append(f'<div class="nl">{html.escape(node.detail)}</div>')
    if node.source:
        lines.append(f'<div class="nf">见于 {html.escape(node.source)}</div>')
    badge_html = f'<span class="badge">{html.escape(badge)}</span>' if node.role == "client" else ""
    return (
        f'<div class="node" style="left:{x}px;top:{y}px;border-color:{color};'
        f'background:{background};border-width:{border_width}">'
        f'<div class="nt" style="color:{color}">{html.escape(node.name)}{badge_html}</div>'
        f'{"".join(lines)}</div>'
    )


def _edges_svg(
    placed: dict[GraphNode, tuple[int, int, int]],
    edges: list[GraphEdge],
) -> tuple[str, list[str]]:
    by_id = {node.id: node for node in placed}
    pair_seen: dict[tuple[str, str], int] = {}
    parts = ['<svg class="edges">', "<defs>"]
    for kind, (color, _, _) in EDGE_STYLE.items():
        parts.append(
            f'<marker id="m-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" '
            f'markerHeight="11" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
        )
    parts.append("</defs>")
    labels: list[str] = []
    for edge in edges:
        start = by_id.get(edge.source)
        end = by_id.get(edge.target)
        if start is None or end is None:
            continue
        x1, y1, h1 = placed[start]
        x2, y2, h2 = placed[end]
        key = tuple(sorted((edge.source, edge.target)))
        index = pair_seen.get(key, 0)
        pair_seen[key] = index + 1
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
        nx, ny = -(y2 - y1) / length, (x2 - x1) / length
        bend = _bend(index, mx, my, nx, ny, placed, start, end)
        cx, cy = mx + nx * bend, my + ny * bend
        sx, sy = _border_point(x1, y1, h1, cx, cy)
        tx, ty = _border_point(x2, y2, h2, cx, cy)
        color, dash, _ = EDGE_STYLE[edge.kind]
        parts.append(
            f'<path d="M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {tx:.1f},{ty:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="2.3" stroke-linecap="round"{_dash_attr(dash)} '
            f'marker-end="url(#m-{edge.kind})"/>'
        )
        if edge.label:
            lx, ly = _label_point(sx, sy, cx, cy, tx, ty, nx, ny, placed)
            label_color = "#555" if edge.kind == "procedure" else color
            labels.append(
                f'<div class="elabel" style="left:{lx:.0f}px;top:{ly:.0f}px;color:{label_color}">'
                f'{html.escape(edge.label).replace(chr(10), "<br>")}</div>'
            )
    parts.append("</svg>")
    return "".join(parts), labels


def _bend(
    index: int,
    mx: float,
    my: float,
    nx: float,
    ny: float,
    placed: dict[GraphNode, tuple[int, int, int]],
    start: GraphNode,
    end: GraphNode,
) -> float:
    """单条连线轻轻弯曲；同一对主体的多条连线分开；避开中间的卡片。"""

    sign = 1 if index % 2 == 0 else -1
    bend = sign * (52.0 if index == 0 else 120.0)
    for node, (node_x, node_y, card_height) in placed.items():
        if node is start or node is end:
            continue
        qx, qy = mx + nx * bend * 0.5, my + ny * bend * 0.5
        if abs(qx - node_x) < CARD_WIDTH / 2 + 24 and abs(qy - node_y) < card_height / 2 + 20:
            side = -1 if (node_x - mx) * nx + (node_y - my) * ny >= 0 else 1
            bend = side * max(abs(bend), 110)
    return bend


def _label_point(
    sx: float,
    sy: float,
    cx: float,
    cy: float,
    tx: float,
    ty: float,
    nx: float,
    ny: float,
    placed: dict[GraphNode, tuple[int, int, int]],
) -> tuple[float, float]:
    """把连线说明放在曲线中段，并挪开卡片，避免压在卡片上。"""

    base_x = 0.25 * sx + 0.5 * cx + 0.25 * tx
    base_y = 0.25 * sy + 0.5 * cy + 0.25 * ty
    for distance in (22, 46, -22, 70, -46):
        x = min(max(base_x + nx * distance, 110), GRAPH_WIDTH - 120)
        y = max(18, base_y + ny * distance)
        if not _hits_card(x, y, placed):
            return x, y
    return base_x, base_y


def _hits_card(x: float, y: float, placed: dict[GraphNode, tuple[int, int, int]]) -> bool:
    for node_x, node_y, card_height in placed.values():
        if abs(x - node_x) < CARD_WIDTH / 2 + 16 and abs(y - node_y) < card_height / 2 + 12:
            return True
    return False


def _border_point(cx: float, cy: float, card_height: int, tx: float, ty: float) -> tuple[float, float]:
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    half_w, half_h = CARD_WIDTH / 2 + 4, card_height / 2 + 2
    scale = min(half_w / abs(dx), half_h / abs(dy))
    return cx + dx * scale, cy + dy * scale


def _dash_attr(dash: str) -> str:
    return f' stroke-dasharray="{dash}"' if dash else ""
