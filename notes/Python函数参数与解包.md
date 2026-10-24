# Python 学习笔记：函数参数与解包

**相关知识：位置参数、关键字参数、`*args`、`**kwargs`、单独的 `*`、参数转发**

阅读顺序：先分清定义和调用，再看收集、限制与解包。本文与[函数与装饰器](./Python函数与装饰器.md)配套；个人理解留待自己补写，不作为学习验收记录。

## 一、五种常见写法速查

| 写法 | 出现位置 | 作用 |
|---|---|---|
| `def f(*args): ...` | 函数定义 | 收集多个位置参数，得到元组 `tuple` |
| `def f(**kwargs): ...` | 函数定义 | 收集未被其他形参接收的关键字参数，得到字典 `dict` |
| `def f(a, *, b): ...` | 函数定义 | `b` 必须通过关键字传入；单独的 `*` 不接收数据 |
| `f(*nums)` | 函数调用 | 将列表等可迭代对象展开为位置参数 |
| `f(**data)` | 函数调用 | 将字典等映射展开为关键字参数，键必须是字符串 |

先记住方向：**定义时收集，调用时展开；定义里的单独 `*` 是分隔标记。**

`args`、`kwargs` 是约定俗成的变量名，可以改成其他名字；语法作用来自 `*` 和 `**`。

## 二、位置参数与关键字参数

```python
def add(a, b):
    return a + b


assert add(1, 2) == 3        # 按位置：a=1，b=2
assert add(a=1, b=2) == 3    # 按名称：a=1，b=2
assert add(b=2, a=1) == 3    # 关键字参数按名称匹配
assert add(1, b=2) == 3      # 位置参数和关键字参数也可以组合
```

这里的 `a`、`b` 都可以按位置或关键字接收。不能因为某次用了 `b=2`，就认为定义中的 `b` 只能按关键字传入。

## 三、`def f(*args)`：收集位置参数

```python
def collect(first, *args):
    return first, args


assert collect("A", 10, 20) == ("A", (10, 20))
assert collect("A") == ("A", ())
assert collect("A", [10, 20]) == ("A", ([10, 20],))
```

- `first` 先接收第一个位置参数。
- 剩余的位置参数收集到 `args`，其类型是元组。
- 没有剩余位置参数时，`args` 是空元组 `()`。
- 传入一个列表，不会自动拆成多个参数：`[10, 20]` 仍是一个参数。

`*args` 不接收多余关键字参数；是否支持关键字参数，要看其他形参以及有没有 `**kwargs`。

## 四、`def f(**kwargs)`：收集关键字参数

```python
def collect(name, **kwargs):
    return name, kwargs


assert collect(name="小雨", age=20, city="上海") == (
    "小雨", {"age": 20, "city": "上海"}
)
assert collect("小雨") == ("小雨", {})
```

`name` 已经由显式形参接收，因此不进入 `kwargs`；其余 `age`、`city` 被收集成字典。没有剩余关键字参数时得到 `{}`。

**关键字参数**指调用时的 `age=20` 这种形式，不是“值为字符串的参数”。例如 `f("age")` 传入的仍是位置参数。

## 五、`def f(a, *, b)`：限制为仅限关键字参数

```python
def format_answer(message, *, language="中文"):
    return f"{language}：{message}"


assert format_answer("你好", language="中文") == "中文：你好"
assert format_answer(message="Hello", language="英语") == "英语：Hello"
assert format_answer("你好") == "中文：你好"

try:
    format_answer("Hello", "英语")
except TypeError:
    pass
else:
    raise AssertionError("language 不能通过位置参数传入")
```

单独的 `*`：

- 不会创建变量，也不会把参数收集成元组。
- 要求后面的普通形参按关键字传入。
- 不限制前面的 `message`；它仍可按位置或关键字传入。

**仅限关键字与是否必填是两个维度。** `def f(a, *, b)` 中的 `b` 没有默认值，必须传；`def f(a, *, b=2)` 中的 `b` 可以省略，但传入时仍要写名称。

如果已经有 `*args`，后面的普通形参也只能通过关键字传入，不再写一个单独的 `*`：

```python
def collect(*args, language="中文", **kwargs):
    return args, language, kwargs


assert collect(1, 2, language="英语", debug=True) == (
    (1, 2), "英语", {"debug": True}
)
assert collect(1, "英语") == ((1, "英语"), "中文", {})
```

第二次调用中的 `"英语"` 进入 `args`，不会按位置匹配到 `language`。

## 六、`f(*nums)` 与 `f(**data)`：调用时解包

```python
def add(a, b):
    return a + b


nums = [1, 2]
data = {"a": 1, "b": 2}

assert add(*nums) == 3     # 相当于 add(1, 2)
assert add(**data) == 3    # 相当于 add(a=1, b=2)
assert add(*[1], **{"b": 2}) == 3

try:
    add(nums)
except TypeError:
    pass
else:
    raise AssertionError("传入列表本身只提供一个参数，缺少 b")
```

`*nums` 也可用于元组、生成器等可迭代对象。`**data` 要求映射的键是字符串；展开后的名称还必须符合被调用函数的参数规则。

解包不会绕过数量、名称或重复传值检查：

```python
def add(a, b):
    return a + b


invalid_calls = [
    lambda: add(*[1, 2, 3]),              # 位置参数过多
    lambda: add(**{"a": 1, "c": 2}),     # 不接受关键字 c
    lambda: add(1, **{"a": 2, "b": 3}),  # a 被重复赋值
    lambda: add(**{1: 10, "b": 20}),      # 关键字名称不是字符串
]

for call in invalid_calls:
    try:
        call()
    except TypeError:
        pass
    else:
        raise AssertionError("该调用应因参数不匹配而失败")
```

## 七、为什么装饰器常用 `*args, **kwargs`

```python
def decorator(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result

    return wrapper


@decorator
def greet(name, *, language="中文"):
    return f"{language}：你好，{name}"


assert greet("小雨", language="中文") == "中文：你好，小雨"
```

同样的星号在两行中方向相反：

1. `def wrapper(*args, **kwargs)`：把调用方的参数收集起来。此例得到 `args == ("小雨",)`、`kwargs == {"language": "中文"}`。
2. `func(*args, **kwargs)`：再展开这些参数，传给原函数。
3. `return result`：把原函数的返回值传回最终调用方。

如果写成 `func(args, kwargs)`，传入的是“一个元组和一个字典”这两个位置参数，含义不同。

包装器能收集任意数量的参数，不代表原函数能接受任意参数；原函数仍会按自己的定义检查。本例只演示同步函数的参数转发；异步函数的包装还需考虑 `async def` 与 `await`，`functools.wraps` 留到后续补充。

## 八、项目中的真实用法

### 1. `generate_reply` 的单独 `*`

`app/services/llm.py` 当前的签名：

```text
async def generate_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    tools: list[dict] | None = None,
    additional_messages: list[dict] | None = None,
    *,
    system_prompt: str = "You are a helpful assistant.",
) -> LLMResult:
```

`system_prompt` 必须通过名称传入，例如项目提取器使用的 `system_prompt=MEMORY_EXTRACTION_PROMPT`。它有默认值，所以可以省略。前面的 `message` 等参数也可以主动用关键字传递，但并没有被这个 `*` 限制为仅限关键字。

### 2. MCP 测试中的收集与转发

`tests/test_agent_mcp.py` 中的局部函数签名与转发语句摘录：

```text
def use_in_process_server(self, server, *args, **kwargs):
    ...
    original_init(self, mcp, *args, **kwargs)
```

测试替换 `server`，把真实构造调用中的服务配置改成同进程 MCP Server；其他位置参数和关键字参数则收集后继续转发。这让测试只调整需要替换的部分。

### 3. 其他位置的 `*`

`app/services/llm.py` 组装消息列表时还使用了 `*history`。它出现在列表内部，是把元素展开到新列表中，不是在定义函数参数。

判断星号含义时，先看上下文。本文聚焦函数定义和调用，乘法、赋值解包等语法另行整理。

## 九、我的理解与待补充

以下由自己补写，Codex 协助核对：

- 我会怎样解释“定义时收集，调用时展开”？
- `f(nums)` 和 `f(*nums)` 在参数数量上有什么区别？
- `*args` 与单独的 `*` 分别解决什么问题？
- 项目为什么让 `system_prompt` 只能按关键字传入？
- 我曾经预测错的调用、实际结果与原因是什么？

## 参考

- [Python 3.12：仅限位置与仅限关键字参数](https://docs.python.org/3.12/tutorial/controlflow.html#special-parameters)
- [Python 3.12：任意数量的参数](https://docs.python.org/3.12/tutorial/controlflow.html#arbitrary-argument-lists)
- [Python 3.12：解包参数列表](https://docs.python.org/3.12/tutorial/controlflow.html#unpacking-argument-lists)
