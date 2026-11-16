"""用飞行行为和模型接口练习 Protocol 与抽象基类。

在仓库根目录运行 uv run python playground/03_class.py 查看打印结果。
OpenAIModel / QwenModel 仅返回演示字符串，不连接任何真实模型 API。
"""

from typing import Protocol

from abc import ABC, abstractmethod

class Flyable(Protocol):
    """用 Protocol 描述调用方需要的 fly 方法，实现类不必显式继承它。"""

    def fly(self) -> None:
        pass

class Bird:
    """通过同名 fly 方法满足 Flyable 的结构要求。"""

    def fly(self) -> None:
        print("鸟会飞")

class Airplane:
    """另一个具有 fly 方法的对象，用于观察同一调用入口如何接收不同实现。"""

    def fly(self) -> None:
        print("飞机会飞")

def start_flying(obj: Flyable):
    """只依赖对象的 fly 行为，不需要知道具体是 Bird 还是 Airplane。"""
    obj.fly()

start_flying(Bird())
start_flying(Airplane())


class Model(ABC):
    """用抽象基类要求子类实现 chat，缺少实现的子类不能直接实例化。"""

    @abstractmethod
    def chat(self, message: str) -> str:
        pass


class OpenAIModel(Model):

    """抽象接口的演示实现，仅拼接字符串，不请求 OpenAI 服务。"""

    def chat(self, message: str) -> str:
        return f"OpenAI: {message}"


class QwenModel(Model):

    """另一个演示实现，便于观察相同接口下可替换的行为。"""

    def chat(self, message: str) -> str:
        return f"Qwen: {message}"


def run_agent(model: Model):
    """调用传入模型的共同 chat 接口；这里只是多态练习，不是正式 Agent 循环。"""
    print(model.chat("你好"))


run_agent(OpenAIModel())
run_agent(QwenModel())
