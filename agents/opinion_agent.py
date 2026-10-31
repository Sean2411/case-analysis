"""法律意见 Agent：只在已确认事实和检索法条的范围内作判断。"""

from __future__ import annotations

from agents.runtime import SHARED_RULES, CompleteFn, call_agent, clip_text
from config import DISCLAIMER
from rag.retriever import RetrievalResult, format_law_hits


def run(
    facts: str,
    doc_relation: str,
    person_relation: str,
    retrieval: RetrievalResult,
    complete: CompleteFn,
    temperature: float,
) -> str:
    system = (
        SHARED_RULES
        + """
阶段：法律意见
任务：基于现有材料给出阶段性法律分析。必须包含：
- 主要风险点
- 建议的下一步行动或路径
- 明确哪些句子是「材料已确认的事实」，哪些句子是「法律判断」
规则：
- 法律判断不能改写或扩充事实。
- 优先引用检索到的法条，并标注来源文件名。
- 检索结果里没有的条文，不要编造条号和原文；如确需提及模型既有知识，要标明「非本次检索结果」。
"""
    )
    if not retrieval.loaded:
        law_rule = f"法规库未加载。法律意见中必须原句写明：{DISCLAIMER}"
    else:
        law_rule = "请优先依据下面的检索片段发表意见。"
    user = (
        "【已确认事实草稿】\n"
        + clip_text(facts, 5000)
        + "\n\n【资料关系草稿】\n"
        + clip_text(doc_relation, 4000)
        + "\n\n【人物关系草稿】\n"
        + clip_text(person_relation, 4000)
        + "\n\n【法规检索】\n"
        + law_rule
        + "\n"
        + format_law_hits(retrieval)
    )
    return call_agent(complete, system, user, temperature)
