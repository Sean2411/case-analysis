"""界面可下载的虚构示例卷宗，自测也用同一份压缩包。"""

from __future__ import annotations

import io
import zipfile

SAMPLE_CONTRACT = """以下内容为虚构演示材料，不对应真实案件。

2024年1月1日，张三（借款人，身份证号材料未附）与李四（出借人）签订《借款合同》。
双方约定：张三向李四借款人民币100000元；借款期限自2024年1月1日至2024年12月31日；年利率8%。
合同写明采用书面形式。张三、李四均在合同末页签名。
合同未约定担保人，也未附抵押登记材料。
"""

SAMPLE_TRANSFER = """# 转账记录（虚构）

- 日期：2024年1月2日
- 付款人：李四
- 收款人：张三
- 金额：人民币100000元
- 备注：借款合同项下出借
- 材料未附银行回单原件，只记载了上述摘要。
"""

SAMPLE_NOTICE = """催收记录（虚构）

2025年1月10日，李四向张三发送短信，催告其归还借款本金100000元及按合同计算的利息。
张三于同日回复：“钱先欠着，年底再说。”
本文件没有记载张三已经还款，也没有记载双方变更过还款期限。
"""


def build_sample_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write(archive, "借款合同.txt", SAMPLE_CONTRACT)
        _write(archive, "转账记录.md", SAMPLE_TRANSFER)
        _write(archive, "催收记录.txt", SAMPLE_NOTICE)
    return buffer.getvalue()


def _write(archive: zipfile.ZipFile, name: str, text: str) -> None:
    info = zipfile.ZipInfo(filename=name)
    # 明确使用 UTF-8 文件名，避免中文在不同系统上乱码。
    info.flag_bits |= 0x800
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, text.encode("utf-8"))
