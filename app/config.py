"""从进程环境变量构造应用配置。

由其他模块导入 settings 使用。这里只读取环境变量，不主动读取 .env；
本地启动命令中的 --env-file 负责把配置加载到进程环境。
"""

import os

from pydantic import BaseModel


# 集中声明应用名、环境、数据库路径及模型连接配置的类型。
class AppConfig(BaseModel):
    app_name: str
    app_env: str
    database_path: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str


def load_config() -> AppConfig:
    """读取进程环境并构造配置，缺失项使用本地学习用默认值。

    这里只获得配置值，不验证远端服务或 API Key 是否可用；不能输出整个配置对象。
    """
    return AppConfig(
        app_name=os.getenv("APP_NAME", "agent-lab"),
        app_env=os.getenv("APP_ENV", "development"),
        database_path=os.getenv("DATABASE_PATH", "agent-lab.db"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
    )


settings = load_config()
