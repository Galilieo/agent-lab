# class User:
#   pass
# user = User()

# class User:
#   def __init__(self, name: str,age: int):
#     self.name = name
#     self.age = age

#   def introduce(self) -> str:
#     return  f"Hi, my name is {self.name} and I am {self.age} years old"
#   def is_adult(self) -> bool:
#     return self.age >= 18
# user=User("Mike", 20)
# print(user.name)
# print(user.age)
# print(user.introduce())
# print(user.is_adult())

# class Animal:
#   def speak(self) -> str:
#     return "发出声音"

# class Dog(Animal):
#   pass
# dog = Dog()
# print(dog.speak())


# 异步调用模型
# import asyncio

# async def call_model(message: str) -> str:
#   print("开始调用模型")

#   await asyncio.sleep(2)

#   return f"模型回答：{message}"

# async def main() -> None:
#   answer = await call_model("你好")
#   print(answer)

# asyncio.run(main())

#pytest 测试框架
# def add(a: int, b: int) -> int:
#   return a + b
# def test_add() -> None:
#   result = add (1, 2)

#   assert result == 3

# 列表推导式
numbers = [1, 2, 3, 4, 5]

squares = []

for number in numbers:
  squares.append(number ** 2)

print(squares)

squares = [number ** 2 for number in numbers]
print(squares)

even_numbers = [
  number for number in numbers if number % 2 == 0
]
print(even_numbers)

messages = [
{"role": "user", "content": "你好"},
{"role": "assistant", "content": "你好"},
{"role": "user", "content": "你叫什么名字"}
]
contests = []
for message in messages:
  if message["role"] == "user":
    contests.append(message["content"])

contests = [message["content"] for message in messages if message["role"] == "user"]
result = [
    message["content"].strip()
    for message in messages
    if message.get("role") == "user"
    and message.get("content")
    and len(message["content"]) > 2
]
contents = [ message["role"] for message in messages]


print(contents)

models = ["GPT", "Claude", "DeepSeek"]

model_status = {}

for model in models:
    model_status[model] = True

print(model_status)

model_status = {
   model: True
   for model in models
}