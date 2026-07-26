#JSON 与文件读写
import json
message = {
    "role": "user",
    "content": "你好",
    "enabled": True
}

json_text = json.dumps(message,ensure_ascii=False)

print(json_text)
print(type(json_text))

json_text = '{"role": "user", "content": "你好", "enabled": true}'

message = json.loads(json_text)
print(message)
print(type(message))

message = [{
    "role": "user",
    "content": "你好",
    "enabled": True
},{
    "role": "user",
    "content": "你叫什么名字",
    "enabled": True}
]

with open(
  "playground/message.json",
  "w",
  encoding="utf-8"
) as file:
  json.dump(message,file,ensure_ascii=False,indent=2)

with open(
  "playground/message.json",
  "r",
  encoding="utf-8"
) as file:
  loaded_messages = json.load(file)

print(loaded_messages)
print(type(loaded_messages))
