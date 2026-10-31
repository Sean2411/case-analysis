"""整理最终 Markdown：补齐三个标题，并在法规库缺失时写入固定提示。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from config import DISCLAIMER, NO_HIT_NOTE, REQUIRED_HEADINGS
from rag.retriever import LawHit


@dataclass
class Drafts:
    doc_relation: str
    person_relation: str
    opinion: str


def strip_wrapping_fence(text: str) -> str:
    stripped = (text or "").strip()
    match = re.match(r"^```(?:markdown|md)?\s*\n([\s\S]*?)\n```$", stripped)
    if match:
        return match.group(1).strip()
    return stripped


def has_required_headings(text: str) -> bool:
    positions = [text.find(heading) for heading in REQUIRED_HEADINGS]
    return all(pos >= 0 for pos in positions) and positions[0] < positions[1] < positions[2]


def assemble_fallback(drafts: Drafts) -> str:
    """汇总 Agent 没有按格式输出时，用三份草稿拼出必需结构。"""

    def body(text: str) -> str:
        cleaned = (text or "").strip()
        return cleaned if cleaned else "（该部分未能生成有效内容）"

    return (
        f"{REQUIRED_HEADINGS[0]}\n\n{body(drafts.doc_relation)}\n\n"
        f"{REQUIRED_HEADINGS[1]}\n\n{body(drafts.person_relation)}\n\n"
        f"{REQUIRED_HEADINGS[2]}\n\n{body(drafts.opinion)}\n"
    )


def _insert_after_opinion(text: str, note: str) -> str:
    if note in text:
        return text
    heading = REQUIRED_HEADINGS[2]
    index = text.find(heading)
    if index < 0:
        return text.rstrip() + "\n\n" + note + "\n"
    end = index + len(heading)
    return text[:end] + "\n\n" + note + "\n" + text[end:]


def _append_citations(text: str, hits: list[LawHit]) -> str:
    if not hits:
        return text
    lines = ["", "### 检索依据（本地法规库）", ""]
    for index, hit in enumerate(hits, start=1):
        lines.append(f"{index}. 来源：`{hit.source}`")
        lines.append(hit.text.strip())
        lines.append("")
    return text.rstrip() + "\n" + "\n".join(lines)


def finalize_markdown(
    raw: str,
    drafts: Drafts,
    *,
    laws_loaded: bool,
    hits: list[LawHit],
) -> str:
    """保证下载结果始终带有三个标题；空法规库时写入规定提示句。"""

    text = strip_wrapping_fence(raw)
    if not has_required_headings(text):
        text = assemble_fallback(drafts)
    else:
        text = text[text.find(REQUIRED_HEADINGS[0]) :].strip()

    if not laws_loaded:
        text = _insert_after_opinion(text, DISCLAIMER)
    elif not hits:
        text = _insert_after_opinion(text, NO_HIT_NOTE)
    else:
        text = _append_citations(text, hits)
    return text.strip() + "\n"


def split_report(markdown: str) -> dict[str, str]:
    """按三个标题切开，供界面分栏展示。失败时返回空字典。"""

    indexes = [markdown.find(heading) for heading in REQUIRED_HEADINGS]
    if any(index < 0 for index in indexes):
        return {}
    if not (indexes[0] < indexes[1] < indexes[2]):
        return {}
    bounds = indexes + [len(markdown)]
    keys = ("doc", "person", "opinion")
    return {key: markdown[bounds[i] : bounds[i + 1]].strip() for i, key in enumerate(keys)}
