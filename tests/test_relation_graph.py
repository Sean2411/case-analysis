"""法律关系图：只在模型给出合法数据时出图，版式按身份分色。"""

from relation_graph import parse_relation_graph, render_relation_html, strip_relation_fence

SAMPLE = """
张三是借款人，李四是出借人。

```relation-graph
{"nodes":[
  {"id":"a","name":"张三","role":"client","subtitle":"借款人","detail":"收到100000元","source":"借款合同.txt"},
  {"id":"b","name":"李四","role":"defendant","subtitle":"出借人","detail":"转出100000元","source":"转账记录.md"},
  {"id":"c","name":"借款本金","role":"object","subtitle":"100000元","detail":"期限至2024-12-31","source":"借款合同.txt"},
  {"id":"d","name":"王五","role":"stranger","subtitle":"见证人","detail":"在场","source":"催收记录.txt"},
  {"id":"e","name":"<script>","role":"third","subtitle":"","detail":"","source":""}
], "edges":[
  {"from":"b","to":"a","kind":"money","label":"2024-01-02转账100000元"},
  {"from":"a","to":"c","kind":"contract","label":"借款合同"},
  {"from":"a","to":"missing","kind":"breach","label":"不应出现"},
  {"from":"a","to":"b","kind":"nope","label":"催收"}
]}
```
"""


def test_parse_keeps_supported_nodes_and_drops_dangling_edges() -> None:
    graph = parse_relation_graph(SAMPLE)
    assert graph is not None
    roles = {node.name: node.role for node in graph["nodes"]}
    assert roles["张三"] == "client"
    assert roles["王五"] == "third"
    assert roles["<script>"] == "third"
    pairs = {(edge.source, edge.target, edge.kind) for edge in graph["edges"]}
    assert ("b", "a", "money") in pairs
    assert ("a", "b", "contract") in pairs
    assert all(edge.target != "missing" for edge in graph["edges"])


def test_invalid_or_missing_graph_is_ignored() -> None:
    assert parse_relation_graph("只有文字，没有图。") is None
    assert parse_relation_graph("```relation-graph\n{bad}\n```") is None
    assert parse_relation_graph('```relation-graph\n{"nodes":[]}\n```') is None


def test_render_uses_reference_colors_and_escapes_text() -> None:
    graph = parse_relation_graph(SAMPLE)
    assert graph is not None
    page, height = render_relation_html(graph)
    assert height > 400
    assert "张三" in page
    assert "一方当事人" in page
    assert "#1f4e79" in page
    assert "#eef4fb" in page
    assert "#b9770e" in page
    assert "#2e8b57" in page
    assert "资金流向" in page
    assert "见于 借款合同.txt" in page
    assert "法律关系图" in page
    assert "主体和人员" in page
    assert "法院认定" not in page
    assert "&lt;script&gt;" in page
    assert strip_relation_fence(SAMPLE).startswith("张三是借款人")
    assert "relation-graph" not in strip_relation_fence(SAMPLE)


def test_cards_do_not_overlap() -> None:
    graph = parse_relation_graph(SAMPLE)
    assert graph is not None
    page, _height = render_relation_html(graph)
    boxes = []
    for node in graph["nodes"]:
        marker = f">{node.name}"
        assert marker in page or node.name == "<script>"
    # 同一身份会纵向错开；不同身份的中心点也不能重合。
    from relation_graph import _layout

    placed, _height = _layout(graph["nodes"])
    points = [(x, y) for x, y, _card_height in placed.values()]
    assert len(points) == len(set(points))
    cards = [(x, y, h) for x, y, h in placed.values()]
    for index, (x1, y1, h1) in enumerate(cards):
        for x2, y2, h2 in cards[index + 1 :]:
            overlap_x = abs(x1 - x2) < 220
            overlap_y = abs(y1 - y2) < (h1 + h2) / 2
            assert not (overlap_x and overlap_y)


def test_court_and_entity_fields_are_rendered_without_invention() -> None:
    text = """
```relation-graph
{"title":"张三诉李四借款合同纠纷","nodes":[{"id":"a","name":"张三","role":"client","subtitle":"借款人","source":"借款合同.txt"}],
 "edges":[],
 "court":{"title":"法院认定（2024-06-01，某市人民法院）","lines":["双方存在借款合同关系"],"source":"判决书.txt"},
 "entities":[{"name":"张三","role":"借款人","org":"","gender":"男","id_no":"<id>","source":"借款合同.txt"}]}
```
"""
    graph = parse_relation_graph(text)
    assert graph is not None
    assert graph["court"].title.startswith("法院认定")
    page, _height = render_relation_html(graph)
    assert "张三诉李四借款合同纠纷" in page
    assert "双方存在借款合同关系" in page
    assert "法院认定（2024-06-01，某市人民法院）" in page
    assert "&lt;id&gt;" in page
    assert "class=\"court\"" in page
