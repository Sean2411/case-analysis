"""项目级常量。界面、分析流程和自测共用这里的文案与上限。"""

from __future__ import annotations

# OpenAI 兼容接口的默认值，可在界面中改成其他服务。
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.2

# 最终 Markdown 必须包含这三个标题，顺序固定。
REQUIRED_HEADINGS = (
    "## 一、资料关系",
    "## 二、人物/法律关系",
    "## 三、法律意见",
)

# 法规库缺失时必须出现的原句，自测会检查它。
DISCLAIMER = "未加载法规库，法律意见仅基于模型已有知识"
NO_HIT_NOTE = "已加载本地法规库，但未检索到与本案材料明显相关的法条。"

# 单个材料过长时截断，避免一次请求塞进整卷宗。
MAX_FILE_CHARS = 8000
# 送入单个 Agent 的材料总长度。超出后按文件均分再截断。
MAX_PROMPT_CHARS = 28000
MAX_ZIP_BYTES = 30 * 1024 * 1024
MAX_ZIP_FILES = 40
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 20 * 1024 * 1024
MAX_PDF_PAGES = 40
MAX_XLSX_SHEETS = 10
MAX_XLSX_ROWS = 200
LAW_CHUNK_CHARS = 800
LAW_TOP_K = 5
LLM_TIMEOUT_SECONDS = 120
LLM_MAX_TOKENS = 4096
