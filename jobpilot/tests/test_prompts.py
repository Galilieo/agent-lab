"""验证提示词文件的加载、名字校验、格式校验，以及「改正文必须升版本」。

加载测试用 tmp_path 中的临时文件替换提示词目录，不依赖真实提示词内容；
锁文件测试检查仓库里真实的 prompts/ 目录。不连接数据库。
"""

from hashlib import sha256
from json import dumps, loads
from pathlib import Path

import pytest

from jobpilot.services import prompts
from jobpilot.services.prompts import PromptFormatError, load_prompt

LOCK_PATH = prompts.PROMPTS_DIR / "versions.lock.json"


@pytest.fixture
def prompts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把提示词目录指向临时目录，测试自己写入需要的文件。"""
    monkeypatch.setattr(prompts, "PROMPTS_DIR", tmp_path)
    return tmp_path


def test_load_prompt_returns_version_text_and_label(prompts_dir: Path) -> None:
    """版本头和分隔线之后的内容是正文，首尾空白被去掉。"""
    (prompts_dir / "parse_jd.txt").write_text(
        "version: 3\n---\n\n请输出 json。\n{jd}\n\n", encoding="utf-8"
    )

    prompt = load_prompt("parse_jd")

    assert prompt.name == "parse_jd"
    assert prompt.version == 3
    assert prompt.text == "请输出 json。\n{jd}"
    assert prompt.label == "parse_jd@3"


@pytest.mark.parametrize(
    "bad_name",
    ["", "../../evals/datasets/resumes/resume-001", "a/b", "Parse_JD", "jd.txt"],
)
def test_load_prompt_rejects_names_outside_prompt_dir(
    prompts_dir: Path, bad_name: str
) -> None:
    """名字会拼进文件路径，只允许小写字母、数字和下划线，防止读到目录外的文件。"""
    with pytest.raises(ValueError, match="提示词名"):
        load_prompt(bad_name)


@pytest.mark.parametrize(
    "content",
    [
        "请输出 json。",  # 没有版本头
        "version: 1\n请输出 json。",  # 没有分隔线
        "version: v1\n---\n请输出 json。",  # 版本不是数字
        "version: 0\n---\n请输出 json。",  # 版本必须从 1 开始
        "author: me\nversion: 1\n---\n请输出 json。",  # 版本头前有别的行
    ],
)
def test_load_prompt_rejects_malformed_header(prompts_dir: Path, content: str) -> None:
    """格式不对时报错并带上文件名，而不是把版本头当成正文发给模型。"""
    (prompts_dir / "broken.txt").write_text(content, encoding="utf-8")

    with pytest.raises(PromptFormatError, match="broken.txt"):
        load_prompt("broken")


def test_every_prompt_file_matches_version_lock() -> None:
    """改了正文却没升版本时失败；升了版本则要求同步更新锁文件。

    锁文件按提示词名记录版本号和正文的 SHA-256。哈希只用来比较内容是否变化，
    不需要保密。
    """
    lock: dict[str, dict[str, object]] = loads(LOCK_PATH.read_text(encoding="utf-8"))
    names = sorted(path.stem for path in prompts.PROMPTS_DIR.glob("*.txt"))

    assert names == sorted(lock), "prompts/ 下的文件与 versions.lock.json 不一致"
    for name in names:
        prompt = load_prompt(name)
        actual = {
            "version": prompt.version,
            "sha256": sha256(prompt.text.encode("utf-8")).hexdigest(),
        }
        locked = lock[name]
        if actual["version"] == locked["version"]:
            assert actual["sha256"] == locked["sha256"], (
                f"{name}.txt 正文已修改，请把 version 升到 {prompt.version + 1}"
            )
        else:
            assert actual == locked, (
                f"{name}.txt 已升版本，请把锁文件中的这一项更新为：\n"
                f"{dumps({name: actual}, ensure_ascii=False, indent=2)}"
            )
