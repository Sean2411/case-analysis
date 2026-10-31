"""本地法规检索。

默认用关键词打分。需要向量检索时，把 embed_fn 传给 retrieve_laws：
embed_fn 接收一段文本，返回等长的浮点向量。未传入时不会访问任何向量服务。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from config import LAW_CHUNK_CHARS, LAW_TOP_K
from parsers.documents import decode_text

# 不依赖分词库。这些词用于把材料里的法律概念对上法条。
TERM_DICT = (
    "借款",
    "贷款",
    "利息",
    "逾期",
    "担保",
    "抵押",
    "质押",
    "保证",
    "保证人",
    "合同",
    "违约",
    "违约金",
    "定金",
    "侵权",
    "损害",
    "赔偿",
    "继承",
    "遗产",
    "遗嘱",
    "代理",
    "委托",
    "股权",
    "出资",
    "股东",
    "公司",
    "劳动",
    "工资",
    "离婚",
    "夫妻",
    "债权",
    "债务",
    "诉讼时效",
    "管辖",
    "证据",
    "所有权",
    "租赁",
    "房屋",
    "买卖",
    "民间借贷",
    "高利",
    "还款",
    "返还",
    "解除",
    "撤销",
    "无效",
    "诉讼",
    "仲裁",
    "执行",
)

STOP_SEGMENTS = {"以及", "或者", "如果", "但是", "因此", "以及其", "我们", "他们", "当事人"}
# 材料文件名里的扩展名不应给所有 .md / .txt 法规加分。
EXTENSION_TOKENS = {"txt", "md", "pdf", "docx", "xlsx", "doc", "zip"}
ARTICLE_RE = re.compile(r"(?=第[0-9零一二三四五六七八九十百千]+条)")
EmbedFn = Callable[[str], Sequence[float]]


@dataclass
class LawHit:
    source: str
    text: str
    score: float


@dataclass
class RetrievalResult:
    """loaded 为 False 表示目录不存在、没有法规文件，或文件都读不出来。"""

    loaded: bool
    hits: list[LawHit]
    warnings: list[str]
    file_count: int


def list_law_files(laws_dir: Path) -> list[Path]:
    if not laws_dir.exists() or not laws_dir.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(laws_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
            files.append(path)
    return files


def inspect_law_library(laws_dir: Path) -> int:
    return len(list_law_files(laws_dir))


def _read_law(path: Path) -> str:
    return decode_text(path.read_bytes())


def _hard_wrap(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    return [text[offset : offset + limit] for offset in range(0, len(text), limit)]


def split_law_text(text: str, source: str) -> list[LawHit]:
    """按「第X条」切开；没有条号时按空行切开。过长片段再按字数切开。"""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []
    parts = [part.strip() for part in ARTICLE_RE.split(cleaned) if part.strip()]
    if len(parts) <= 1:
        parts = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    chunks: list[LawHit] = []
    for part in parts:
        for piece in _hard_wrap(part, LAW_CHUNK_CHARS):
            chunks.append(LawHit(source=source, text=piece, score=0.0))
    return chunks


def _terms(text: str) -> list[str]:
    found: list[str] = []
    for term in TERM_DICT:
        if term in text:
            found.append(term)
    for segment in re.split(r"[^\u4e00-\u9fffA-Za-z0-9]+", text):
        token = segment.strip()
        if token.lower() in EXTENSION_TOKENS:
            continue
        if 2 <= len(token) <= 20 and token not in STOP_SEGMENTS:
            found.append(token)
        elif token.isascii() and len(token) >= 2:
            found.append(token.lower())
    unique: list[str] = []
    seen: set[str] = set()
    for term in found:
        if term not in seen:
            seen.add(term)
            unique.append(term)
    return unique[:80]


def _keyword_score(query_terms: list[str], chunk: LawHit) -> float:
    score = 0.0
    haystack = chunk.text
    # 只用文件名本身加分，避免路径和扩展名碰到短词就命中。
    source_stem = Path(chunk.source).stem
    for term in query_terms:
        count = haystack.count(term)
        if count:
            score += min(count, 5) * (len(term) ** 1.2)
        if len(term) >= 2 and term in source_stem:
            score += len(term)
    return score


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _load_chunks(laws_dir: Path) -> RetrievalResult:
    files = list_law_files(laws_dir)
    if not files:
        return RetrievalResult(loaded=False, hits=[], warnings=[], file_count=0)

    chunks: list[LawHit] = []
    warnings: list[str] = []
    for path in files:
        source = str(path.relative_to(laws_dir)).replace("\\", "/")
        try:
            text = _read_law(path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"法规文件无法读取，已跳过：{source}（{exc}）")
            continue
        if not text.strip():
            warnings.append(f"法规文件为空，已跳过：{source}")
            continue
        chunks.extend(split_law_text(text, source))

    if not chunks:
        return RetrievalResult(loaded=False, hits=[], warnings=warnings, file_count=len(files))
    return RetrievalResult(loaded=True, hits=chunks, warnings=warnings, file_count=len(files))


def retrieve_laws(
    laws_dir: Path,
    query: str,
    *,
    top_k: int = LAW_TOP_K,
    embed_fn: EmbedFn | None = None,
) -> RetrievalResult:
    """检索相关法条。库为空时 loaded=False 且 hits 为空，由上层跳过 RAG。"""

    loaded = _load_chunks(laws_dir)
    if not loaded.loaded:
        return loaded

    ranked: list[LawHit]
    if embed_fn is None:
        terms = _terms(query)
        ranked = []
        for chunk in loaded.hits:
            score = _keyword_score(terms, chunk)
            if score > 0:
                ranked.append(LawHit(source=chunk.source, text=chunk.text, score=score))
    else:
        # 预留的向量路径：只在调用方提供 embed_fn 时启用，失败则退回关键词。
        try:
            query_vector = list(embed_fn(query))
            ranked = []
            for chunk in loaded.hits:
                score = _cosine(query_vector, list(embed_fn(chunk.text)))
                if score > 0:
                    ranked.append(LawHit(source=chunk.source, text=chunk.text, score=score))
        except Exception as exc:  # noqa: BLE001
            loaded.warnings.append(f"向量检索失败，已改用关键词匹配：{exc}")
            terms = _terms(query)
            ranked = []
            for chunk in loaded.hits:
                score = _keyword_score(terms, chunk)
                if score > 0:
                    ranked.append(LawHit(source=chunk.source, text=chunk.text, score=score))

    ranked.sort(key=lambda item: (-item.score, item.source, item.text))
    return RetrievalResult(
        loaded=True,
        hits=ranked[:top_k],
        warnings=loaded.warnings,
        file_count=loaded.file_count,
    )


def format_law_hits(result: RetrievalResult) -> str:
    """把检索结果写成可放进提示词的文本。空库和无命中的提示不同。"""

    if not result.loaded:
        return "未加载法规库。不得声称已经检索本地法条。"
    if not result.hits:
        return "已加载本地法规库，但没有检索到明显相关的法条。不要编造法条编号或原文。"
    lines = ["以下片段来自本地法规库。引用时保持原文并标注来源文件名，不要把法条说成案件事实。"]
    for index, hit in enumerate(result.hits, start=1):
        lines.append(f"（{index}）来源：{hit.source}\n{hit.text.strip()}")
    return "\n\n".join(lines)
