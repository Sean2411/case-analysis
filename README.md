# 案件材料智能分析

在浏览器里上传一个案件材料 zip，系统解析其中的文档，并生成三部分结果：资料关系、人物/法律关系、法律意见。

分析会区分「材料里已经写明的事实」和「法律判断」。材料没有记载的金额、日期、主体和行为，不会被补写成事实。

本工具用于整理和辅助思考，不能代替律师的正式意见。

## 环境

- Python 3.10 或更高版本
- 可访问的 OpenAI 兼容接口。默认按 DeepSeek 填写，也可以换成其他服务

## 安装与启动

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

macOS 上系统通常没有 `python` 和 `streamlit` 这两个命令。依赖装在 `.venv` 里，每次新开终端都要先激活，否则会提示 `command not found`。程序文件名是 `app.py`。

Windows 激活虚拟环境使用 `.venv\Scripts\activate`。

浏览器打开终端里显示的本地地址（一般是 `http://localhost:8501`）。

## 使用

1. 打开页面后直接上传材料。接口固定为 DeepSeek，地址和模型写在 `config.py`，密钥写在 `local_secrets.py`，页面上不显示这些配置。
2. 准备 zip。可以先点「下载示例材料（zip）」，再把这个文件传上去。示例内容是虚构的借款材料。
3. 查看已解析文件。解析失败的文件会标出原因，其余文件仍可继续分析。
4. 点击「开始分析」。
5. 在三个分页中阅读结果，或点「下载分析结果（Markdown）」。

压缩包请小于 30MB，内含 `.docx`、`.pdf`、`.xlsx`、`.txt`、`.md`。扫描版 PDF 往往提取不到文字，需要先做文字识别。单个文件送入模型前最多保留约 8000 字，过长内容会截断，并在界面上提示。

API Key 放在 `local_secrets.py`，该文件已加入 `.gitignore`，不要把它提交到仓库。材料文本会发送到 `config.py` 里配置的接口。

### 切换模型

界面使用 OpenAI 兼容的 Chat Completions。要换服务，改 `config.py` 里的 `DEFAULT_BASE_URL`、`DEFAULT_MODEL` 和 `DEFAULT_TEMPERATURE`：

| 服务 | Base URL | 模型名称示例 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| Kimi | `https://api.moonshot.ai/v1` | `kimi-k3.1-pro` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 其他兼容服务 | 服务商给出的地址，需要 `/v1` 时把路径写进 Base URL | 服务商的模型名 |

## 准备法规库

法规文本放在 `data/laws/`，使用 `.txt` 或 `.md`。可以按子目录分类。程序每次分析时从该目录读取，不会让模型自行下载法规。

建议一个文件放一部法规或一个主题，并用「第X条」起段，例如：

```text
第六百七十六条 借款人未按照约定的期限返还借款的，应当按照约定或者国家有关规定支付逾期利息。
```

UTF-8 最稳妥，GBK 也可以读取。检索默认是关键词匹配：材料和法律词表里的词会跟法条片段打分，取得分最高的若干条，注入法律意见 Agent 和汇总 Agent 的提示词。正式结果里会附上「检索依据」，并标注来源文件名。

`rag/retriever.py` 的 `retrieve_laws(..., embed_fn=...)` 预留了向量检索。传入一个「文本 → 向量」的函数就会改走余弦相似度；向量调用失败时会退回关键词匹配。当前界面不启用向量检索。

仓库里带有两份演示节选，只为让检索能跑通：

- `data/laws/民法典_借款合同_演示节选.md`
- `data/laws/民法典_诉讼时效_演示节选.md`

正式使用前请换成权威公布文本。如果删掉 `data/laws/` 里的全部 `.txt` 和 `.md`，或目录不存在，分析仍会继续，但结果和界面都会写明：

> 未加载法规库，法律意见仅基于模型已有知识

法规库里有文件、但没有对上本案用词时，会提示已加载法规库、未检索到明显相关法条，不会假装引用了法条。

## 分析流程

五个模型步骤加一次本地检索，按这个顺序进行：

1. 材料摘要 Agent：按文件提取要点，只记录材料中已出现的事实。
2. 资料关系 Agent：文件的作用，以及引用、支撑、时序；区分核心证据和程序文件。
3. 人物关系 Agent：当事人身份和法律关系。有把握时可以给出 mermaid。
4. 法规检索：从 `data/laws/` 取相关片段。这一步不调用模型。
5. 法律意见 Agent：在事实和检索片段上形成风险点和下一步，并分开写事实与法律判断。
6. 汇总 Agent：合并为下面的三个标题，并检查有没有把判断写成事实。

如果汇总结果缺少标题，程序会用三份草稿拼回规定格式。法规库为空时，程序会把降级提示写进法律意见，不依赖模型是否记得这句话。

最终 Markdown 以这三个标题开头，顺序固定：

```markdown
## 一、资料关系
## 二、人物/法律关系
## 三、法律意见
```

## 自测

自测不需要 API Key，也不访问网络。它会在内存里生成一个小 zip（含示例材料，以及 docx、pdf、xlsx、txt、md），并用模拟的模型回复跑完整条分析流程。

先完成上面的安装。新开的终端里先执行 `source .venv/bin/activate`，再任选一种：

```bash
pytest tests/ -v
```

```bash
python tests/self_test.py
```

全部通过时，pytest 会显示 `passed`，`python tests/self_test.py` 的最后一行是「自测通过。」，退出码为 0。

自测覆盖：

| 检查项 | 对应用例 |
| --- | --- |
| docx、pdf、xlsx、txt、md 能解析；损坏文件不会拖垮整个压缩包 | `test_parse_supported_formats` |
| 示例 zip、GBK 文本、超长截断、不安全路径 | `test_parse_sample_zip_and_gbk_truncation` |
| zip 损坏或不是 zip 时给出明确错误 | `test_bad_zip_has_friendly_error` |
| 法规库目录不存在或为空时继续分析，并写入规定提示句 | `test_empty_law_library_degrades` |
| 检索到的法条进入法律意见提示词，结果中带来源 | `test_law_retrieval_injects_source` |
| 有法规库但没有命中时，不显示「未加载法规库」 | `test_loaded_library_without_hits_is_not_called_empty` |
| 示例 zip 端到端输出三个必需标题 | `test_output_has_three_headings_on_sample_zip` |
| 汇总 Agent 没按格式输出时，仍然补齐三个标题 | `test_malformed_summary_still_has_headings` |
| API Key 缺失、401、连接失败时的中文提示 | `test_api_failure_message` |
| 没有可用文本时不调用模型 | `test_refuse_when_no_text` |

用例集中在 `tests/test_analysis.py`。

## 目录

```text
app.py                 界面与主流程
sample_case.py         虚构示例 zip
config.py              标题、提示句、长度上限
errors.py              可展示给用户的错误
parsers/documents.py   zip 与各文件解析
rag/retriever.py       法规加载、关键词检索、向量接口
agents/                五个 Agent 与编排
report.py              三个标题的整理与下载文本
data/laws/             本地法规文本
tests/test_analysis.py 自测用例
tests/self_test.py     自测入口
```

## 常见问题

**上传按钮显示为 Upload。**  
这是 Streamlit 文件控件自带的文字，旁边的标题和说明是中文。上传体积上限为 30MB。

**提示压缩包损坏或不是 zip。**  
请重新打包。加密压缩包无法读取，需要先解除密码。

**某个 PDF 解析失败。**  
多半是扫描件或加密文件。该文件会标失败，其他文件继续参与分析。

**提示未加载法规库。**  
`data/laws/` 里没有可用的 `.txt` 或 `.md`。放进法规文本后重新点击分析即可，不必重启也可以读到新文件。

**模型调用失败。**  
先核对 API Key、Base URL 和模型名称。连接失败、超时、额度不足都会显示对应的中文说明。

**结果里的事实和材料对不上。**  
长文件会被截断，被截断的部分不会进入分析。汇总步骤会尽量删掉无原文支持的具体事实，但仍需要人工核对原文。

## 局限

- 关键词检索会漏掉同义但用词不同的法条，正式办案应换上完整、权威的文本，并人工复核引用。
- 演示节选不是现行文本的完整汇编。
- 人物关系图使用 mermaid 代码块，界面按 Markdown 展示。
- 多个 Agent 会连续调用模型，材料和接口耗时都会影响等待时间。
