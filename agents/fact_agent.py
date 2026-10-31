"""材料摘要 Agent：只整理各文件里已经写明的内容。"""

from __future__ import annotations

from agents.runtime import SHARED_RULES, CompleteFn, call_agent
from parsers.documents import Document, render_for_prompt


def run(
    documents: list[Document],
    complete: CompleteFn,
    temperature: float,
    material_text: str | None = None,
) -> str:
    system = (
        SHARED_RULES
        + """
阶段：材料摘要
任务：按文件提取关键内容，并列出已确认事实。
输出：
### 各文件要点
- 《文件名》：只用该文件里写明的信息概括其内容
### 已确认事实
- [文件名] 事实陈述
不要做法律评价，不要推测当事人动机，不要补充材料没有的数字或日期。
"""
    )
    source = material_text if material_text is not None else render_for_prompt(documents)[0]
    user = "请只根据下列案件材料提取要点和已确认事实。\n\n" + source
    return call_agent(complete, system, user, temperature)
