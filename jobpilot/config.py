"""读取仓库根目录配置，提供数据库连接信息和各用途的模型参数。"""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

REPO_ROOT = Path(__file__).resolve().parent.parent


class ModelPurpose(StrEnum):
    """声明网关支持的调用用途，枚举值与 Settings 的配置字段名一致。"""

    EXTRACT_FACTS = "extract_facts"
    PARSE_JD = "parse_jd"
    ORDER_OCR = "order_ocr"
    MATCH = "match"
    PLAN = "plan"
    REWRITE = "rewrite"
    GROUND_CHECK = "ground_check"
    AGENT = "agent"


class ModelSettings(BaseModel):
    """声明可由环境变量调整的模型参数；网关按用途读取。

    输出格式等与提示词、解析器绑定的约定不在此处，由调用方传给网关。
    """

    model_name: str = "deepseek-flash"
    thinking: bool = False
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int = Field(default=2048, gt=0)


class Settings(BaseSettings):
    """加载本地配置；环境变量优先于 .env，同名默认值最后使用。"""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="JOBPILOT_",
        env_nested_delimiter="__",
        extra="ignore",
        hide_input_in_errors=True,
    )

    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_host: str = Field(default="127.0.0.1", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(
        default=5432, validation_alias="POSTGRES_PORT", ge=1, le=65535
    )
    postgres_test_db: str = Field(
        default="jobpilot_test", validation_alias="POSTGRES_TEST_DB"
    )

    deepseek_api_key: SecretStr = Field(default="", validation_alias="OPENAI_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        validation_alias="OPENAI_BASE_URL",
    )
    cookie_name: str = "jobpilot_session"
    cookie_max_age_seconds: int = Field(default=604800, gt=0)
    database_connect_timeout_seconds: int = Field(default=5, gt=0)

    extract_facts: ModelSettings = Field(default_factory=ModelSettings)
    parse_jd: ModelSettings = Field(default_factory=ModelSettings)
    match: ModelSettings = Field(default_factory=ModelSettings)
    plan: ModelSettings = Field(default_factory=ModelSettings)
    rewrite: ModelSettings = Field(default_factory=ModelSettings)
    ground_check: ModelSettings = Field(default_factory=ModelSettings)
    order_ocr: ModelSettings = Field(default_factory=ModelSettings)
    agent: ModelSettings = Field(default_factory=ModelSettings)

    def model_for_purpose(self, purpose: str) -> ModelSettings:
        """按用途查找模型配置，未知用途立即报错。"""
        return getattr(self, ModelPurpose(purpose).value)

    @property
    def database_url(self) -> URL:
        """组装开发库 URL，让 SQLAlchemy 正确处理密码中的特殊字符。"""
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def test_database_url(self) -> URL:
        """复用连接参数，只把目标切换到独立测试库。"""
        return self.database_url.set(database=self.postgres_test_db)


settings = Settings()
