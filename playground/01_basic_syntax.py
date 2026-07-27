# name = "Galilieo"
# age = 20
# project = "agent-lab"

# print(f"我叫{name}，今年{age}岁，我正在做一个项目叫{project}。")
# print(f"明年我将是{age+1}岁。")

# list 列表
# models = ["gpt-5","deepseek","claude"]
# print(type(models))
# print(models[0])
# models[1] = "gemini"

# print(models)

# models.append("deepseek")

# print(models,len(models))

# for model in models:
#   print(f"模型名称：{model}")

# print("遍历结束")

# 字典 dict
# user ={
#   "name":"Galileo",
#   "age":20,
#   "is_student":True
# }
# print(type(user))

# print(user['name'])

# user["age"] = 21
# user["city"] = "Shanghai"

# print(user)
# print(user.get("name"))

# models = [
#   {"name" : "gpt-5", "company":"OpenAI"},
#   {"name" : "gemini", "company":"Google"},
#   {"name" : "claude", "company":"Anthropic"}
# ]

# for model in models:
#   print(f"模型名称:{model["name"]}, 公司:{model['company']}")
# print("遍历结束")
# print(models[0]["name"])

# for model in models:
#   if model["name"] != "claude":
#     print(model["name"])

# if,else,elif
# score = 80
# if score>=90:
#   print("优秀")
# elif score>=80:
#   print("良好")
# elif score>=60:
#   print("及格")
# else:
#   print("不及格")


# def 函数
# def say_hello(name):
#   print(f"Hello,{name}")

# say_hello("Java")

# def add(a,b):
#   return a + b

# print(f"结果是：{add(1,2)}")

# def greet(name,message="你好"):
#   print(f"{message},{name}")

# greet("Galileo")
# greet("Galileo","早上好")
# greet(name="Galileo",message="晚上好")

# def call_model(message,model="gpt",temperature=0.5):
#   return f"调用模型{model} 回答{message}，温度为{temperature}"

# result = call_model(message="你好，世界！",temperature=0.3)

# print(result)

# 类型标注

# name: str = "Galileo"
# age: int = 20
# is_student: bool = True

# def greet(name: str, message: str = "你好"):
#   print(f"{message}, {name}")

# def add(a: int, b: int) -> int:
#   return a + b

# def create_message(role: str, content: str) -> dict:
#   return {"role": role, "content": content}


# None
# result = None

# if result is None:
#   print("结果为空")

# def say_hello():
#   print("Hello, World!")
# result = say_hello()
# print(f"函数返回值是：{result}")

# user = {
#   "name": "Galilieo"
# }
# age = user.get("age")
# print(f"用户年龄是：{age}")

# in /not in
# models = ["GPT","Claude","Gemini"]

# if "GPT" in models:
#   print("支持 GPT")

# if "DeepSeek" not in models:
#   print("展示不支持DeepSeek")

# message = "请帮我介绍 FastAPI"

# if "FastAPI" in message:
#   print("用户正在询问 FastAPI")

# user = {
#   "name": "Galilieo",
#   "age": 20
# }
# if "Galilieo" in user.values():
#   print("存在这个值")
# if "name" in user:
#   print("存在 name 字段")

# allowed_roles = ["user", "assistant", "system"]
# role = "user"

# if role not in allowed_roles:
#     print("消息角色不合法")
# else:
#     print("消息角色合法")
# range
# for number in range(4):
#   print(number)

# for number in range(1,4):
#   print(number)

# for number in range(0,6,2):
#   print(number)

# enumerate
# count = 1
# while count <= 3:
#   print(count)
#   count+=1

# models = ["GPT","Claude","Gemini"]

# for index,model in enumerate(models,start=1):
#   print(f"第{index}个模型是{model}")

# #tuple 元组

# models = ("GPT","OpenAI")
# print(type(models))

# print(models[0])
# print(models[1])
# # 元组不能修改 models[1] = "Claude"

# model = ("GPT","OpenAI")
# name,provider = model
# print(model.index("GPT"))
# print(name)
# print(provider)

# set 集合

# models = {"GPT","Claude","GPT","Gemini"}

# print(type(models))
# print(models)

# models.add("DeepSeek")

# print(models)

# if "GPT" in models:
#   print("GPT在集合中")

# tags = ["Python","FastAPI","Python","Language"]
# unique_tags = set(tags)
# print(unique_tags)
# unique_tags = list(set(tags))
# print(unique_tags)

# date=set()

# 列表切片
# models = ["GPT","Claude","DeepSeek"]

# print(models[1:3])
# print(models[:2])
# print(models[2:])
# copied_models = models[:]
# models = ["GPT", "Claude", "DeepSeek", "Gemini"]

# print(models[-2])

# models.remove("Claude")
# print(models)
# models.pop(1)

# 遍历字典dict
# model = {
#   "name" : "GPT",
#   "provider" : "OpenAI",
#   "price" : 0.03
# }

# for key in model:
#   print(key)
# for key,value in model.items():
#   print(key,value)
# for value in model.values():
#   print(value)

# del model["price"]

# 异常处理 try...except

# try:
#   age = int(input("请输入年龄："))
#   print(f"你输入的年龄是：{age}")
# except ValueError as error:
#   print(f"错误信息{error}")

# try:
#     age = int("20")
# except ValueError:
#   print("格式错误")
# else:
#   print(f"转换成功，年龄是 {age}")
# finally:
#   print("程序结束")

#import 导包
