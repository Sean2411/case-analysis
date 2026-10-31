"""资料关系 Agent：说明文件之间的引用、支撑和时序，并区分证据与程序文件。"""

from __future__ import annotations

from agents.runtime import SHARED_RULES, CompleteFn, call_agent, clip_text
from parsers.documents import Document


def run(
    documents: list[Document],
    facts: str,
    material_text: str,
    complete: CompleteFn,
    temperature: float,
) -> str:
    system = (
        SHARED_RULES
        + """
阶段：资料关系
任务：分析文件之间的关系。只根据材料本身，不要把法律结论写进这一部分。
请覆盖三点：
1. 关键文件及其作用。
2. 文件之间的引用、支撑、时序关系。材料没有写明的关系，标注「材料未载明」，不要臆造“相互印证”。
3. 哪些更接近核心证据，哪些更接近程序文件（如委托、送达、身份证明）。依据来自文件名称和正文，不确定就写不确定。
用条理清楚的列表输出。
"""
    )
    names = "\n".join(f"- {doc.name}" + (f"（解析失败：{doc.error}）" if doc.error else "") for doc in documents)
    user = (
        "【文件清单】\n"
        + names
        + "\n\n【事实摘要】\n"
        + clip_text(facts, 6000)
        + "\n\n【材料原文】\n"
        + material_text
    )
    return call_agent(complete, system, user, temperature)
