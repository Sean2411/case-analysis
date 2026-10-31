"""汇总 Agent：合并三部分，并检查有没有把判断写成事实。"""

from __future__ import annotations

from agents.runtime import SHARED_RULES, CompleteFn, call_agent, clip_text
from config import DISCLAIMER, REQUIRED_HEADINGS
from rag.retriever import RetrievalResult, format_law_hits


def run(
    facts: str,
    doc_relation: str,
    person_relation: str,
    opinion: str,
    material_text: str,
    retrieval: RetrievalResult,
    complete: CompleteFn,
    temperature: float,
) -> str:
    headings = "\n".join(REQUIRED_HEADINGS)
    if retrieval.loaded:
        law_instruction = "保留法律意见中的法条原文和来源文件名，不要删除检索依据。"
    else:
        law_instruction = f"法律意见部分必须包含这句原话：{DISCLAIMER}"
    system = (
        SHARED_RULES
        + f"""
阶段：汇总
任务：把上游草稿整理成一份最终结果，并做一致性检查。
检查时删除或改写任何材料原文和事实草稿都支持不了的具体事实（姓名、日期、金额、行为）。
法律判断可以保留，但必须看得出它是判断，而不是材料已记载的事实。
最终输出只能使用下面三个标题，按顺序出现，不要写开场白：
{headings}
{law_instruction}
如果人物关系草稿里有 relation-graph 代码块，原样放在「## 二、人物/法律关系」正文末尾，不要改成 mermaid，也不要改里面的 JSON。
"""
    )
    user = (
        "【事实草稿】\n"
        + clip_text(facts, 4000)
        + "\n\n【资料关系草稿】\n"
        + clip_text(doc_relation, 4000)
        + "\n\n【人物关系草稿】\n"
        + clip_text(person_relation, 4000)
        + "\n\n【法律意见草稿】\n"
        + clip_text(opinion, 5000)
        + "\n\n【法规检索】\n"
        + format_law_hits(retrieval)
        + "\n\n【原文摘录，用于核对，不得超出摘录范围新增事实】\n"
        + clip_text(material_text, 6000)
    )
    return call_agent(complete, system, user, temperature)
