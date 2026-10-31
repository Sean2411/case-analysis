"""案件材料智能分析的 Streamlit 界面。业务逻辑在 agents、parsers、rag 中。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from agents.llm import chat_complete, locked_temperature
from agents.pipeline import AnalysisResult, run_analysis
from config import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DISCLAIMER,
    NO_HIT_NOTE,
)
from errors import AnalysisError, LLMCallError, ParseError
from parsers.documents import ParseOutcome, parse_zip_bytes
from relation_graph import parse_relation_graph, render_relation_html, strip_relation_fence
from report import split_report

try:
    from local_secrets import DEEPSEEK_API_KEY
except ImportError:
    DEEPSEEK_API_KEY = ""

ROOT = Path(__file__).resolve().parent
LAWS_DIR = ROOT / "data" / "laws"


def main() -> None:
    st.set_page_config(page_title="案件材料智能分析", layout="wide", initial_sidebar_state="collapsed")
    _init_state()
    _render_workspace(_runtime_config())


def _init_state() -> None:
    st.session_state.setdefault("zip_token", None)
    st.session_state.setdefault("outcome", None)
    st.session_state.setdefault("result", None)


def _api_key() -> str:
    """本地读 local_secrets.py；云端读环境变量或平台密钥。"""

    local_key = DEEPSEEK_API_KEY.strip()
    if local_key:
        return local_key
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        return str(st.secrets["DEEPSEEK_API_KEY"]).strip()
    except Exception:
        return ""


def _runtime_config() -> dict[str, object]:
    return {
        "base_url": DEFAULT_BASE_URL,
        "api_key": _api_key(),
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
    }


def _render_workspace(config: dict[str, object]) -> None:
    st.title("案件材料智能分析")
    st.caption("上传案件材料压缩包后，系统会整理资料关系、人物/法律关系和法律意见。材料里没有写明的内容不会被补写成事实。本工具只做辅助整理，不构成正式法律意见。")

    st.subheader("上传材料")
    uploaded = st.file_uploader("上传案件材料（zip）", type=["zip"])
    if uploaded is None:
        st.session_state.zip_token = None
        st.session_state.outcome = None
        st.session_state.result = None
        st.info("请上传包含 .docx、.pdf、.xlsx、.txt、.md 的 zip 压缩包。")
        return

    payload = uploaded.getvalue()
    token = hashlib.sha256(payload).hexdigest()
    if token != st.session_state.zip_token:
        # 换了压缩包就重新解析，并清掉上一份分析结果。
        st.session_state.zip_token = token
        st.session_state.result = None
        try:
            st.session_state.outcome = parse_zip_bytes(payload)
        except ParseError as exc:
            st.session_state.outcome = None
            st.error(str(exc))
            return

    outcome: ParseOutcome | None = st.session_state.outcome
    if outcome is None:
        return
    _render_files(outcome)
    _render_analyze(config, outcome)
    result: AnalysisResult | None = st.session_state.result
    if result is not None:
        _render_result(result)


def _render_files(outcome: ParseOutcome) -> None:
    st.subheader("已解析文件")
    if not outcome.documents and outcome.warnings:
        for warning in outcome.warnings:
            st.warning(warning)
        return
    for warning in outcome.warnings:
        st.caption(warning)
    for doc in outcome.documents:
        if doc.error:
            state = "解析失败"
        elif not doc.ok:
            state = "无可用文本"
        elif doc.truncated:
            state = "已截断"
        else:
            state = "可分析"
        line = f"- `{doc.name}` · {state} · 原文 {doc.char_count} 字符"
        if doc.error:
            line += f" · {doc.error}"
        st.markdown(line)


def _render_analyze(config: dict[str, object], outcome: ParseOutcome) -> None:
    ready = any(doc.ok for doc in outcome.documents)
    if not ready:
        st.warning("没有可用于分析的文本。请检查文件格式，扫描版 PDF 需要先做文字识别。")
    if not st.button("开始分析", type="primary", disabled=not ready):
        return

    st.session_state.result = None
    missing = _missing_config(config)
    if missing:
        st.error(missing)
        return

    forced = locked_temperature(str(config["base_url"]), str(config["model"]))
    if forced is not None and abs(float(config["temperature"]) - forced) > 1e-6:
        st.info(f"该模型只允许温度为 {forced:g}，本次分析已自动按此温度调用。")

    def complete(messages: list[dict[str, str]], temperature: float) -> str:
        return chat_complete(
            messages,
            base_url=str(config["base_url"]),
            api_key=str(config["api_key"]),
            model=str(config["model"]),
            temperature=temperature,
        )

    with st.status("正在分析案件材料", expanded=True) as status:
        try:
            result = run_analysis(
                outcome.documents,
                complete=complete,
                laws_dir=LAWS_DIR,
                temperature=float(config["temperature"]),
                progress=st.write,
            )
        except (LLMCallError, AnalysisError) as exc:
            status.update(label="分析未完成", state="error")
            st.error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            status.update(label="分析未完成", state="error")
            st.error(f"分析过程出现未预期错误：{exc}")
            return
        st.session_state.result = result
        status.update(label="分析完成", state="complete")


def _missing_config(config: dict[str, object]) -> str:
    if not config["base_url"]:
        return "未配置 Base URL。请在 config.py 中填写 DEFAULT_BASE_URL。"
    if not config["api_key"]:
        return "未配置 API Key。请在项目根目录的 local_secrets.py 中填写 DEEPSEEK_API_KEY。"
    if not config["model"]:
        return "未配置模型名称。请在 config.py 中填写 DEFAULT_MODEL。"
    return ""


def _render_result(result: AnalysisResult) -> None:
    st.subheader("分析结果")
    if not result.laws_loaded:
        st.info(DISCLAIMER)
    elif not result.law_hits:
        st.warning(NO_HIT_NOTE)
    else:
        st.success(f"已从本地法规库检索到 {len(result.law_hits)} 条相关片段，并写入法律意见。")

    notes = [item for item in result.warnings if item not in {DISCLAIMER, NO_HIT_NOTE}]
    for note in notes:
        st.warning(note)

    st.download_button(
        "下载分析结果（Markdown）",
        data=result.markdown.encode("utf-8"),
        file_name="案件分析结果.md",
        mime="text/markdown",
        key="download_result_md",
    )

    sections = split_report(result.markdown)
    if not sections:
        st.markdown(result.markdown)
        return

    doc_tab, person_tab, opinion_tab = st.tabs(["资料关系", "人物/法律关系", "法律意见"])
    doc_tab.markdown(sections["doc"])
    graph = getattr(result, "relation_graph", None) or parse_relation_graph(sections["person"])
    if graph:
        graph_html, graph_height = render_relation_html(graph)
        with person_tab:
            components.html(graph_html, height=graph_height, scrolling=False)
    person_tab.markdown(strip_relation_fence(sections["person"]))
    opinion_tab.markdown(sections["opinion"])
    with st.expander("查看完整 Markdown"):
        st.markdown(result.markdown)


if __name__ == "__main__":
    main()
