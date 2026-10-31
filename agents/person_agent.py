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
在文字说明之后，如果材料足以标出主体和关系，再输出一段关系图，放在 ```relation-graph 代码块里，内容必须是合法 JSON。
节点和连线只能使用材料中出现的主体和关系。没有把握就不要输出这个代码块，也不要输出空的 JSON。
格式如下。材料没有的字段不要编造，直接省略；法院没有写明认定时不要写 court。
label 可以用 \\n 分成两三行短句。性别、出生日期、民族、公民身份号码、住址、电话、执业证号只有材料原文写了才能填。
```relation-graph
{"title":"材料中的案由或案件名称","nodes":[{"id":"a","name":"姓名或机构","role":"client","subtitle":"材料写明的身份","detail":"一句事实","source":"文件名"}],"edges":[{"from":"a","to":"b","kind":"money","label":"第一行事实\\n第二行事实"}],"court":{"title":"法院认定（日期，法院）","lines":["材料写明的认定"],"source":"文件名"},"entities":[{"name":"姓名","role":"身份","org":"所属机构","source":"文件名"}]}
```
role 只能是 client（一方当事人）、defendant（相对方）、object（标的或争议焦点）、third（案外第三方）。
kind 只能是 contract（合同关系）、money（资金流向）、breach（违约或请求）、procedure（程序事项）。
"""
    )
    user = "【事实摘要】\n" + clip_text(facts, 6000) + "\n\n【材料原文】\n" + material_text
    return call_agent(complete, system, user, temperature)
