"""演示从同目录模块导入函数并调用。

在仓库根目录运行 uv run python playground/use_calculator.py。
直接执行脚本时，脚本所在的 playground 目录可用于查找 calculator 模块。
"""

from calculator import add

result = add(1, 2)

print(result)

# import calculator

# result = calculator.add(10, 20)

# print(result)
