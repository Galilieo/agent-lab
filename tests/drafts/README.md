# 学习测试草稿

这里保存尚未完成的学习任务，不代表已经通过的回归保护。

## 当前草稿

`chat_memory_draft.py` 是聊天后的记忆接线测试。已有 fake 模型、临时 SQLite、成功与失败场景，以及学习者参考示例写出的断言；生产接线尚未实现，部分断言仍有字典键名等结构差异待核对。

2026-10-26 归档前完整运行结果为 **3 failed、62 passed**：保存成功与显式保存失败场景缺少目标反馈，普通失败场景先遇到断言键名错误。因此尚未确认这一主题的正确 RED，也不能将这三例计入通过基线。

文件名不匹配 pytest 默认的 `test_*.py` / `*_test.py`，所以普通 `pytest -q` 不收集它。这只用于保存当前学习现场，不是删除或跳过此前已经通过的测试。`tests/conftest.py` 保留自动记忆提取的默认 fake 隔离，服务层测试仍使用各自的 fake HTTP。

## 继续学习

从仓库根目录操作：

1. 先读正式学习路线和导师提示词，保持“共同拆解、一个核心任务先尝试”的过渡方式。
2. 对照 `read_chat_state()` 的返回结构自行核对现有断言；已看过的完整示例不记为独立测试设计证据。
3. 恢复测试文件名：

   ```bash
   mv tests/drafts/chat_memory_draft.py tests/test_chat_memory.py
   ```

4. 运行目标测试，确认失败由缺少接线行为造成，再进入核心 SQL 与编排的自主尝试：

   ```bash
   uv run --offline pytest -q tests/test_chat_memory.py
   ```

5. GREEN 后运行完整回归；只有实际验证通过才更新基线或完成状态。

如果只想检查草稿能否收集而暂不恢复，可显式指定文件：

```bash
uv run --offline pytest --collect-only -q tests/drafts/chat_memory_draft.py
```

显式指定文件也能执行草稿，默认不收集不代表这些场景已经通过。
