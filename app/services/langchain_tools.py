"""将原生计算器适配为 LangChain 工具，复用既有参数和计算规则。

工具声明供模型选择；执行由调用方触发，不创建模型客户端或写入数据库。
参数校验及计算异常向调用方传播，由 Agent 编排层决定如何处理。
"""

from langchain_core.tools import StructuredTool

from app.tools import CalculatorArguments, run_calculator


def calculate_numbers(
    left: int | float,
    operator: str,
    right: int | float,
) -> int | float:
    """将独立工具参数转换为原生参数对象，复用已有计算器。"""
    arguments = CalculatorArguments(
        left=left,
        operator=operator,
        right=right,
    )
    return run_calculator(arguments)


def build_calculator_tool() -> StructuredTool:
    """包装计算器执行函数、名称、描述和参数模型，不立即执行计算。"""
    return StructuredTool.from_function(
        func=calculate_numbers,
        name="calculator",
        description="执行两个数字的基础数学计算",
        args_schema=CalculatorArguments,
    )
