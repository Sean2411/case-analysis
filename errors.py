"""面向使用者的错误。界面直接展示这些异常的文字。"""

from __future__ import annotations


class AppError(Exception):
    """分析过程中可以安全展示给用户的错误。"""


class ParseError(AppError):
    """压缩包整体无法读取。单个文件失败不使用这个异常。"""


class LLMCallError(AppError):
    """模型接口调用失败，或返回了无法使用的内容。"""


class AnalysisError(AppError):
    """材料不足以开始分析，或流程无法继续。"""
