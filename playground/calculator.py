"""供导入练习使用的加法、乘法函数。

由 use_calculator.py 导入；与 app/tools.py 中带参数校验的 Agent 工具相互独立。
"""

def add(a: int,b: int) -> int:
  """返回两个整数的和，供导入练习调用。"""
  return a + b

def multiply(a: int,b: int) -> int:
  """返回两个整数的积，与加法一起演示模块中的多个函数。"""
  return a * b
