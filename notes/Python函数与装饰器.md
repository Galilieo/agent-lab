# Python 学习笔记：函数与装饰器

**重要程度：⭐⭐⭐⭐⭐**

**相关知识：函数对象、名称绑定、作用域、内部函数、闭包、装饰器**

本文根据个人原始笔记整理，保留已有理解，并补充概念边界与项目中的对应位置。学习进度仍以[总体学习路线](./agent-lab总体学习路线.md)为准。

## 一、在项目中解决什么问题

阅读以下代码时，需要理解：`@` 后面是谁、什么时候执行、原函数什么时候被调用。

- `app/schemas.py` 中的 `@model_validator(mode="after")`：声明模型级校验逻辑。
- `app/main.py` 中的路由装饰器：把请求路径与处理函数关联起来。
- `tests/test_memory_extraction.py` 中的 `@pytest.mark.parametrize(...)`：声明多组测试输入。
- `app/mcp_server.py` 中的 `@mcp.tool()`：把函数注册为 MCP 工具。

这些都是装饰器的应用，但不意味着它们都用同一种 `wrapper` 实现。

## 二、函数对象、调用与返回值

Python 函数也是对象，可以赋值给变量、作为参数传入，也可以作为返回值交出去。

```python
def hello():
    print("Hello")


a = hello
a()  # Hello

b = hello()  # Hello
print(b)     # None
```

| 写法 | 含义 |
|---|---|
| `hello` | 获取名称 `hello` 当前绑定的对象，这里是函数对象 |
| `hello()` | 调用该函数，表达式的结果是函数的返回值 |
| `a = hello` | 让 `a` 也引用同一个函数对象，不调用函数 |
| `b = hello()` | 先调用函数，再把返回值赋给 `b` |

上例中的 `hello()` 只打印内容，没有显式 `return`，因此返回 `None`。打印内容与返回值是两件事。

**我的理解（来自原稿，措辞校准）：** 不加括号是在传递函数对象；加括号是在调用函数。更准确地说，函数名是一个名称，可以被重新绑定，并不是函数对象本身。

函数作为参数时，接收方可以决定什么时候调用它：

```python
def run(func):
    print("开始执行")
    func()
    print("执行结束")


run(hello)
```

输出依次为 `开始执行`、`Hello`、`执行结束`。这里传入的是 `hello`，不是 `hello()` 的返回值。

## 三、内部函数与作用域

```python
def outer():
    print("A")

    def inner():
        print("B")

    return inner


f = outer()  # A
f()          # B
```

执行过程：

1. 调用 `outer()`，打印 `A`。
2. 执行 `def inner`，创建函数对象，并把它绑定到局部名称 `inner`。
3. `return inner` 把函数对象交给调用方，此时没有打印 `B`。
4. `f` 接收该对象；调用 `f()` 才执行内部函数体。

在这个独立例子中，直接在外部写 `inner()` 会触发 `NameError`，因为外部没有绑定这个名称。拿到函数对象后，仍可以通过 `f()` 调用它。

也可以写成 `outer()()`：第一个 `()` 调用 `outer`，第二个 `()` 调用它返回的函数。

**我的理解（来自原稿）：** 内部函数一般只能在外部函数内部直接通过名字调用。如果要从外面调用，需要通过 `return` 或其他方式暴露它的引用。

需要区分：执行 `def` 会创建函数对象，但不会因此执行函数体。默认参数、装饰器等定义时行为与函数体执行是不同的事。

## 四、`return inner` 与 `return inner()`

| 写法 | 是否调用 `inner` | 返回什么 |
|---|---|---|
| `return inner` | 否 | 函数对象 |
| `return inner()` | 是 | 调用的结果；没有显式返回值时为 `None` |

```python
def outer():
    def inner():
        print("Hello")

    return inner()


x = outer()  # Hello
print(x)     # None
```

`return inner()` 完全合法；如果目的是把函数交出去供以后调用，就应该写 `return inner`。

## 五、装饰器：处理函数，再重新绑定名称

常见的函数装饰器接收原函数，返回一个包装函数：

```python
def decorator(func):
    def wrapper():
        print("执行前")
        result = func()
        print("执行后")
        return result

    return wrapper


@decorator
def hello():
    print("Hello")
    return "完成"


answer = hello()
print(answer)
```

输出：

```text
执行前
Hello
执行后
完成
```

对于这个例子，`@decorator` 可以理解为：先定义原函数，再执行 `hello = decorator(hello)`。

- 外层的 `return wrapper`：把包装函数交出去。
- 内层的 `return result`：把原函数的返回值传给最终调用方。

如果 `wrapper` 只调用 `func()` 却不返回结果，调用方拿到的就会是 `None`。本例只支持无参数函数，带参数的转发例子见[函数参数与解包](./Python函数参数与解包.md#七为什么装饰器常用-args-kwargs)。

**我的理解（来自原稿）：** `@` 是应用装饰器的语法，后面的 `decorator` 才是实际负责处理函数的部分。

更一般地说，装饰器是可调用对象，可以返回包装函数、原函数或其他对象；具体行为取决于实现。

## 六、装饰与调用发生在不同的时机

```python
def decorator(func):
    print("A")

    def wrapper():
        print("B")
        return func()

    return wrapper


@decorator
def hello():
    print("C")


print("D")
hello()
```

输出：

```text
A
D
B
C
```

| 时机 | 发生的事情 | 输出 |
|---|---|---|
| 执行到被装饰的函数定义 | 调用 `decorator`，创建并返回 `wrapper`，重新绑定 `hello` | `A` |
| 执行后续普通代码 | 调用 `print("D")` | `D` |
| 调用 `hello()` | 执行 `wrapper`，再通过 `func()` 调用原函数 | `B`、`C` |

装饰发生在执行到函数定义语句时；若该定义位于模块顶层，通常是在模块首次导入或作为脚本执行时。包装函数的调用时机则由后续代码决定。

对于 `@model_validator(mode="after")` 这类写法，还可以分成两步理解：先调用 `model_validator(mode="after")` 得到装饰器，再把定义出的函数交给它。不能据此认为自定义校验函数体也会在定义时执行。

## 七、原函数为什么还能被调用：闭包

在上面的包装例子中，`hello` 被重新绑定，不代表原函数对象立即消失：

```text
hello → wrapper
            └── 通过闭包访问 func → 原函数
```

`wrapper` 使用了外层函数的局部变量 `func`。即使 `decorator()` 已经返回，`wrapper` 仍能访问这个变量，这就是此处闭包的作用。

一个更小的例子：

```python
def outer():
    x = 100

    def inner():
        return x

    return inner


f = outer()
print(f())  # 100
```

这里保留的是对所需外层变量绑定的访问，不是把整个外层执行过程永久保存，也不应理解成对变量值拍了一张永远不变的快照。并非所有内部函数都需要闭包。

如果想保留原函数的直接入口，可以在重新绑定前写 `original_hello = hello`，之后分别通过 `original_hello()` 与装饰后的 `hello()` 调用。

## 八、回到项目：注册、标记与校验

| 装饰器 | 主要作用 | 当前阅读重点 |
|---|---|---|
| `@pytest.fixture` | 声明测试夹具，由 pytest 管理使用 | 声明夹具不代表立即执行夹具函数体 |
| `@pytest.mark.parametrize(...)` | 声明多组测试参数 | 参数声明与测试运行分开理解 |
| `@model_validator(mode="after")` | 声明字段校验后的模型级校验 | 自定义函数体在模型校验流程中执行 |
| `@app.get(...)` / `@app.post(...)` | 注册 HTTP 路由 | 路由注册与请求到来时执行处理函数是不同阶段 |
| `@mcp.tool()` | 注册 MCP 工具 | 工具注册与工具调用是不同阶段 |

`app/schemas.py` 中的 `validate_action(self)` 就属于第三类：字段校验成功后，Pydantic 调用它检查 `action` 与 `memories` 是否匹配，合法时把 `self` 返回给校验流程。详见 [Pydantic 与 schemas](./Pydantic与schemas.md)。

## 九、复习时检查的几个误区

- **把打印当作返回：** `print(...)` 显示内容，不会替函数返回业务结果。
- **把名称当成对象本身：** `hello = ...` 改变名称绑定，不等于修改原函数的函数体。
- **把内部函数定义当作调用：** 执行到 `def wrapper` 不会因此执行 `wrapper` 的函数体。
- **把装饰器都理解成包装器：** 注册、标记等装饰器也符合装饰语法，不一定套用本例的实现。
- **把闭包当成值的快照：** 它让内部函数继续访问所需外层变量。

## 十、我的后续补充

以下留给自己结合源码填写，不作为已经掌握的记录：

- 用自己的话解释：项目里的 `validate_action` 在什么时候执行？
- 写一个曾经预测错输出的例子，记录预测、实际输出与原因。
- `*args`、`**kwargs` 与参数转发已整理到[函数参数与解包](./Python函数参数与解包.md)，可结合示例补写自己的理解；后续再补 `functools.wraps` 与带参数装饰器的完整用法。

## 参考

- [Python 3.12：函数定义与装饰器](https://docs.python.org/3.12/reference/compound_stmts.html#function-definitions)
- [Python 3.12：名称绑定与作用域](https://docs.python.org/3.12/reference/executionmodel.html#resolution-of-names)
- [Pydantic：模型校验器](https://docs.pydantic.dev/latest/concepts/validators/#model-validators)
