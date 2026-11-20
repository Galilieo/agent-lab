"""从 prompts/ 读取提示词文件，返回正文和版本号，供网关写入调用记录。

文件格式：第一行 `version: <正整数>`，第二行 `---`，其后是正文。
"""

import re
from dataclasses import dataclass

from jobpilot.config import REPO_ROOT

PROMPTS_DIR = REPO_ROOT / "jobpilot" / "prompts"

# 名字会拼进文件路径；不允许 . 和 /，防止读到目录外的文件。
_NAME_PATTERN = re.compile(r"[a-z0-9_]+")
_HEADER_PATTERN = re.compile(r"version: ([1-9]\d*)")
_SEPARATOR = "\n---\n"


class PromptFormatError(ValueError):
    """提示词文件缺少版本头或分隔线。"""


@dataclass(frozen=True)
class Prompt:
    """一个提示词文件的内容和版本。"""

    name: str
    version: int
    text: str

    @property
    def label(self) -> str:
        """写入 model_call.prompt_version 时使用的标识，形如 parse_jd@1。"""
        return f"{self.name}@{self.version}"


def load_prompt(name: str) -> Prompt:
    """按名字读取 prompts/{name}.txt，解析版本头并返回去掉首尾空白的正文。"""
    if not _NAME_PATTERN.fullmatch(name):
        raise ValueError(f"非法的提示词名：{name!r}")
    path = PROMPTS_DIR / f"{name}.txt"
    header, separator, body = path.read_text(encoding="utf-8").partition(_SEPARATOR)
    match = _HEADER_PATTERN.fullmatch(header)
    if not separator or match is None:
        raise PromptFormatError(
            f"{path.name} 第一行应为 'version: <正整数>'，第二行应为 '---'"
        )

    return Prompt(name=name, version=int(match.group(1)), text=body.strip())
