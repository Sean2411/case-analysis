"""按固定顺序跑完六个步骤，并整理成可下载的 Markdown。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agents import doc_relation_agent, fact_agent, opinion_agent, person_agent, summary_agent
from agents.runtime import CompleteFn
from config import DISCLAIMER, NO_HIT_NOTE
from errors import AnalysisError
from parsers.documents import Document, render_for_prompt
from rag.retriever import EmbedFn, LawHit, RetrievalResult, retrieve_laws
from report import Drafts, finalize_markdown

ProgressFn = Callable[[str], None]


@dataclass
class AnalysisResult:
    markdown: str
    warnings: list[str]
    laws_loaded: bool
    law_hits: list[LawHit]


def run_analysis(
    documents: list[Document],
    *,
    complete: CompleteFn,
    laws_dir: Path,
    temperature: float = 0.2,
    progress: ProgressFn | None = None,
    embed_fn: EmbedFn | None = None,
) -> AnalysisResult:
    """事实抽取 → 资料关系 → 人物关系 → 法规检索 → 法律意见 → 汇总。

    法规检索不调用模型。库为空时仍继续分析，并在结果中写入固定降级提示。
    """

    usable = [doc for doc in documents if doc.ok]
    if not usable:
        raise AnalysisError(
            "没有成功解析出文本内容。请确认压缩包内包含 .docx、.pdf、.xlsx、.txt 或 .md，"
            "且不是扫描件或加密文件。"
        )

    def step(message: str) -> None:
        if progress:
            progress(message)

    warnings: list[str] = []
    for doc in documents:
        if doc.error:
            warnings.append(f"{doc.name}：{doc.error}")

    material_text, shrunk = render_for_prompt(documents)
    if any(doc.truncated for doc in documents) or shrunk:
        warnings.append("部分材料因长度限制被截断后才送入模型，分析范围以截断后的文本为准。")

    step("正在提取材料要点")
    facts = fact_agent.run(documents, complete, temperature, material_text)
    step("正在分析资料关系")
    doc_relation = doc_relation_agent.run(documents, facts, material_text, complete, temperature)
    step("正在梳理人物与法律关系")
    person_relation = person_agent.run(facts, material_text, complete, temperature)

    # 用原文而不是模型摘要做检索，避免摘要改写后对不上法条用词。
    step("正在检索本地法规")
    query = material_text + "\n" + facts
    retrieval: RetrievalResult = retrieve_laws(laws_dir, query, embed_fn=embed_fn)
    warnings.extend(retrieval.warnings)
    if not retrieval.loaded:
        warnings.append(DISCLAIMER)
    elif not retrieval.hits:
        warnings.append(NO_HIT_NOTE)

    step("正在形成法律意见")
    opinion = opinion_agent.run(facts, doc_relation, person_relation, retrieval, complete, temperature)
    step("正在汇总并检查一致性")
    summary = summary_agent.run(
        facts,
        doc_relation,
        person_relation,
        opinion,
        material_text,
        retrieval,
        complete,
        temperature,
    )
    drafts = Drafts(doc_relation=doc_relation, person_relation=person_relation, opinion=opinion)
    markdown = finalize_markdown(
        summary,
        drafts,
        laws_loaded=retrieval.loaded,
        hits=retrieval.hits,
    )
    return AnalysisResult(
        markdown=markdown,
        warnings=warnings,
        laws_loaded=retrieval.loaded,
        law_hits=list(retrieval.hits),
    )
