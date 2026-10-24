# Pydantic 与 schemas：常用方法和项目理解

**相关知识：数据契约、模型实例、JSON、字段约束、模型级校验**

**适用版本：本项目使用的 Pydantic v2**

本文整理常用方法与当前源码，个人理解区用于逐步补充，不代表新的学习验收或功能完成状态。

## 一、`schemas.py` 是什么

`schemas.py` 是项目自己命名的 Python 模块，不是一个提供固定方法的库。项目在其中定义数据模型，用来描述数据应该有哪些字段、字段类型是什么、应满足哪些约束。

当前 `app/schemas.py` 中：

| 模型 | 职责 |
|---|---|
| `HealthResponse` | 健康检查响应 |
| `ChatRequest` | 聊天请求字段 |
| `ChatResponse` | 聊天成功响应字段 |
| `MemoryCandidate` | 单条记忆候选的结构与约束 |
| `MemoryExtractionResult` | 整体提取结果，以及动作与候选列表的关系 |

这些类继承 Pydantic 的 `BaseModel`，所以可以使用它提供的方法。自定义的 `validate_action` 则由项目自己编写。

## 二、常用方法：输入与输出

| 写法 | 输入 | 输出 | 用途 |
|---|---|---|---|
| `Model(**data)` | 关键字参数 | 模型实例 | 创建并校验实例 |
| `Model.model_validate(data)` | 字典等 Python 数据 | 模型实例 | 校验已有数据 |
| `Model.model_validate_json(text)` | JSON 字符串，也支持 bytes 等 | 模型实例 | 解析 JSON 并校验 |
| `obj.model_dump()` | 已有模型实例 | Python 字典 | 测试断言、后续数据处理 |
| `obj.model_dump_json()` | 已有模型实例 | JSON 字符串 | JSON 序列化 |
| `Model.model_json_schema()` | 模型定义及可选配置 | 描述结构的字典 | 查看或提供 JSON Schema |

`Model` 表示模型类，例如 `MemoryExtractionResult`；`obj` 表示实例，例如 `result`。

`model_json_schema()` 描述“数据应该长什么样”，不会返回某次提取的实际内容，也不会自己调用 LLM 或保证 LLM 按这个结构输出。

`model_dump()` 默认生成 Python 模式的数据，像日期这样的值不一定已经变成 JSON 可序列化的类型；需要时可使用 `mode="json"`。本项目当前这些字符串、列表字段不涉及此差异。

## 三、一个完整的数据转换例子

在项目根目录的 Python 环境中运行：

```python
from app.schemas import MemoryCandidate, MemoryExtractionResult

payload = {
    "action": "upsert",
    "memories": [
        {"scope": "user", "key": "answer_language", "value": " 中文 "},
    ],
}

result = MemoryExtractionResult.model_validate(payload)

assert isinstance(result, MemoryExtractionResult)
assert isinstance(result.memories, list)
assert isinstance(result.memories[0], MemoryCandidate)
assert result.memories[0].value == "中文"

data = result.model_dump()
assert isinstance(data, dict)
assert data["memories"][0]["value"] == "中文"

text = result.model_dump_json()
assert isinstance(text, str)

restored = MemoryExtractionResult.model_validate_json(text)
assert restored.model_dump() == data
```

这段代码展示了三种不同的数据形态：

```text
Python 字典 → model_validate → 模型实例
模型实例 → model_dump → Python 字典
模型实例 → model_dump_json → JSON 字符串
JSON 字符串 → model_validate_json → 模型实例
```

注意：`result.memories` 是列表；`result.memories[0]` 才是一个 `MemoryCandidate` 实例。`model_dump()` 会递归导出这些嵌套模型。

## 四、声明规则与调用方法分开理解

| 当前源码中的写法 | 作用 |
|---|---|
| `Field(min_length=1)` | 声明最小长度约束 |
| `Field(default_factory=list)` | 缺少该字段时，为每个实例创建一个新列表 |
| `Literal["upsert", "skip"]` | 限定动作只能是这两个值 |
| `ConfigDict(extra="forbid")` | 拒绝未声明的额外字段 |
| `ConfigDict(str_strip_whitespace=True)` | 去掉适用字符串字段的首尾空白，不删除内容中间的空格 |
| `@model_validator(mode="after")` | 在字段校验成功后，执行自定义模型级校验 |

这些是类型、字段配置或装饰器，不是与 `model_dump()` 同类的实例方法。

当前两个记忆模型都声明了 `extra="forbid"`；其他模型并未因此自动获得相同配置。`MemoryCandidate` 声明的字符串处理配置也应按该模型的作用范围理解。

## 五、`self`、`return self` 与校验异常

当前 `MemoryExtractionResult.validate_action` 的职责是：

- `upsert` 必须有至少一条候选。
- `skip` 必须没有候选。
- 合法时 `return self`。

调用 `MemoryExtractionResult.model_validate(payload)` 时，可以把本例的流程理解为：

1. Pydantic 校验字段，并将候选数据构建为嵌套模型。
2. 字段校验成功后，调用 `validate_action(self)`。
3. 此处的 `self` 是正在校验的 `MemoryExtractionResult` 实例。
4. 校验器把合法实例返回给 Pydantic，再由外层调用返回给变量 `result`。

`return self` 不代表保存到数据库。该 `after` 校验器应返回实例；漏写会破坏返回契约，不能认为 Pydantic 一定会自动补回实例。

```python
from pydantic import ValidationError

from app.schemas import MemoryExtractionResult

try:
    MemoryExtractionResult.model_validate({"action": "upsert", "memories": []})
except ValidationError as exc:
    assert exc.errors()[0]["type"] == "value_error"
else:
    raise AssertionError("空 upsert 应校验失败")
```

这里自定义校验器抛出的 `ValueError` 会被 Pydantic 纳入 `ValidationError`。不要把它扩大成“校验器内的任何异常都会被包装”。

## 六、放回记忆提取链路

当前 `app/services/memory.py` 的 `extract_memories()` 在拿到 LLM 调用结果后，执行：

```text
result.answer 中的正文字符串
    → MemoryExtractionResult.model_validate_json(...)
    → 结构合法的记忆提取结果，或 ValidationError
```

上游 HTTP 成功、外层响应 JSON 有效，不代表正文也是合法的提取 JSON。这里负责检查正文的数据契约。

结构合法也不代表用户归属正确、来源可靠，或者记忆已经写入数据库。身份与来源绑定、是否允许保存等业务约束，需要由后续应用逻辑处理。此处只解释函数职责，不据此声称完整自动提取链路已经接通。

## 七、我的理解与待补充

以下由自己补写，Codex 可以协助核对；不预先写成已经掌握的结论：

- 我会怎样区分字典、模型实例和 JSON 字符串？
- 为什么 `result.memories` 与 `result.memories[0]` 的类型不一样？
- 为什么模型校验成功还不能直接说“记忆保存成功”？
- 我曾经混淆的调用、当时的预测与实际结果是什么？

## 参考

- [Pydantic：模型及常用方法](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic：模型级校验器](https://docs.pydantic.dev/latest/concepts/validators/#model-validators)
- 项目源码：`app/schemas.py`、`app/services/memory.py`。
- 项目现有测试：`tests/test_memory_extraction.py`。
