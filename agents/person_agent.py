"""人物关系 Agent：抽取当事人身份，以及材料能够支持的法律关系。"""

from __future__ import annotations

from agents.runtime import SHARED_RULES, CompleteFn, call_agent, clip_text


def run(facts: str, material_text: str, complete: CompleteFn, temperature: float) -> str:
    system = (
        SHARED_RULES
        + """
阶段：人物关系
任务：列出材料中出现的主要当事人、身份，以及他们之间的关系。
关系类型可以包括债权债务、侵权、代理、继承、出资、担保等。只有材料写明或直接记载的关系才能列出。
对仅凭法律经验才能认定的关系，单独放在「待核实」中，不要写成既定事实。
可以附加一段 mermaid flowchart，节点只能使用材料中出现的名称。没有把握就不画图。
"""
    )
    user = "【事实摘要】\n" + clip_text(facts, 6000) + "\n\n【材料原文】\n" + material_text
    return call_agent(complete, system, user, temperature)
