# 1.11 app/core/config.py
# 应用配置模块
#
# 这个文件定义了应用程序的所有配置项，从环境变量中读取配置值。
# 配置类会随着工具的加入越来越长。
# 使用Pydantic Settings可以自动从.env文件或环境变量加载配置，并进行类型验证。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型（比如类方法返回自身类型）
from __future__ import annotations

# 从pydantic导入Field和model_validator
# Field: 用于定义字段的额外信息，如默认值、别名、验证规则等
# model_validator: 用于定义模型级别的验证器，可以验证多个字段之间的关系
from pydantic import Field, model_validator

# 从pydantic_settings导入BaseSettings和SettingsConfigDict
# BaseSettings: Pydantic的配置类基类，可以自动从环境变量读取配置
# SettingsConfigDict: 用于配置Settings类的行为，如env_file指定环境变量文件
from pydantic_settings import BaseSettings, SettingsConfigDict

# 从项目的枚举模块导入Env和JwtAlg
# Env: 运行环境枚举（dev, prod, staging等）
# JwtAlg: JWT加密算法枚举（HS256, RS256）
from app.core.enums import Env, JwtAlg

# 从安全默认值模块导入安全头相关的默认值
# 这些默认值定义在security_defaults.py文件中
from app.core.security_defaults import (
    DEFAULT_HSTS_MAX_AGE,  # HSTS默认最大存活时间（1年）
    DEFAULT_PERMISSIONS_POLICY,  # 权限策略默认值（禁止地理位置、麦克风、摄像头）
    DEFAULT_REFERRER_POLICY,  # Referrer策略默认值（no-referrer）
    DEFAULT_X_FRAME_OPTIONS,  # X-Frame-Options默认值（DENY）
)


# 定义Settings类，继承自BaseSettings
# 这个类集中管理所有应用配置
class Settings(BaseSettings):
    # 配置模型的行为
    # SettingsConfigDict 是Pydantic v2的配置方式
    # env_file=".env" 表示从.env文件读取环境变量
    # env_file_encoding="utf-8" 指定环境变量文件的编码格式
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 应用基础配置
    # env: 运行环境，默认使用开发环境（dev）
    # Field(default=Env.dev, alias="ENV") 表示：
    #   - default=Env.dev: 默认值是Env.dev枚举
    #   - alias="ENV": 从环境变量"ENV"读取，如果没找到就用默认值
    env: Env = Field(default=Env.dev, alias="ENV")

    # app_name: 应用名称，默认"enterprise-assistant"
    app_name: str = Field(default="enterprise-assistant", alias="APP_NAME")

    # log_level: 日志级别，默认"INFO"
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # 数据库配置
    # database_url: 数据库连接URL，必填项
    # Field(..., alias="DATABASE_URL") 中的...表示这个字段是必需的，没有默认值
    database_url: str = Field(..., alias="DATABASE_URL")

    # redis_url: Redis连接URL，必填项
    redis_url: str = Field(..., alias="REDIS_URL")

    # 消息队列配置
    # rabbitmq_url: RabbitMQ连接URL，必填项
    rabbitmq_url: str = Field(..., alias="RABBITMQ_URL")

    # celery_result_backend: Celery任务结果后端，默认使用Redis
    celery_result_backend: str = Field(default="redis://127.0.0.1:6379/1", alias="CELERY_RESULT_BACKEND")

    # celery_task_always_eager: 是否同步执行任务（测试用），默认False
    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    # 搜索引擎配置（Elasticsearch）
    # elasticsearch_url: ES连接URL，默认本地9200端口
    elasticsearch_url: str = Field(default="http://127.0.0.1:9200", alias="ELASTICSEARCH_URL")

    # elasticsearch_username: ES用户名，可选
    elasticsearch_username: str | None = Field(default=None, alias="ELASTICSEARCH_USERNAME")

    # elasticsearch_password: ES密码，可选
    elasticsearch_password: str | None = Field(default=None, alias="ELASTICSEARCH_PASSWORD")

    # elasticsearch_verify_certs: 是否验证证书，默认False（开发环境用）
    elasticsearch_verify_certs: bool = Field(default=False, alias="ELASTICSEARCH_VERIFY_CERTS")

    # 数据库连接池配置
    # db_pool_size: 连接池大小，默认10
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")

    # db_max_overflow: 连接池最大溢出连接数，默认20
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    # db_pool_recycle: 连接回收时间（秒），默认1800（30分钟）
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")

    # db_pool_timeout: 获取连接的超时时间（秒），默认30
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")

    # Redis连接池配置
    # redis_max_connections: 最大连接数，默认50
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    # redis_socket_connect_timeout: 连接超时（秒），默认2
    redis_socket_connect_timeout: int = Field(default=2, alias="REDIS_SOCKET_CONNECT_TIMEOUT")

    # redis_socket_timeout: 读写超时（秒），默认2
    redis_socket_timeout: int = Field(default=2, alias="REDIS_SOCKET_TIMEOUT")

    # redis_health_check_interval: 健康检查间隔（秒），默认30
    redis_health_check_interval: int = Field(default=30, alias="REDIS_HEALTH_CHECK_INTERVAL")

    # JWT配置
    # jwt_secret: JWT密钥，必填项
    jwt_secret: str = Field(..., alias="JWT_SECRET")

    # jwt_issuer: JWT签发者，默认"enterprise-assistant"
    jwt_issuer: str = Field(default="enterprise-assistant", alias="JWT_ISSUER")

    # jwt_alg: JWT加密算法，默认HS256
    jwt_alg: JwtAlg = Field(default=JwtAlg.HS256, alias="JWT_ALG")

    # Token过期时间配置
    # access_token_expire_minutes: 访问令牌过期时间（分钟），默认30
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # refresh_token_expire_days: 刷新令牌过期时间（天），默认14
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # 权限同步配置
    # auto_sync_authz: 是否自动同步权限，默认True
    auto_sync_authz: bool = Field(default=True, alias="AUTO_SYNC_AUTHZ")

    # 安全头配置
    # security_headers_enabled: 是否启用安全头，默认True
    security_headers_enabled: bool = Field(default=True, alias="SECURITY_HEADERS_ENABLED")

    # csp: 内容安全策略，可选，默认None
    csp: str | None = Field(default=None, alias="CSP")

    # HSTS配置
    # security_hsts_enabled: 是否启用HSTS，默认False
    security_hsts_enabled: bool = Field(default=False, alias="SECURITY_HSTS_ENABLED")

    # security_hsts_max_age: HSTS最大存活时间，使用默认值31536000（1年）
    security_hsts_max_age: int = Field(default=DEFAULT_HSTS_MAX_AGE, alias="SECURITY_HSTS_MAX_AGE")

    # security_hsts_include_subdomains: 是否包含子域名，默认True
    security_hsts_include_subdomains: bool = Field(default=True, alias="SECURITY_HSTS_INCLUDE_SUBDOMAINS")

    # security_hsts_preload: 是否加入HSTS预加载列表，默认False
    security_hsts_preload: bool = Field(default=False, alias="SECURITY_HSTS_PRELOAD")

    # 其他安全头配置
    # security_x_frame_options: X-Frame-Options，使用默认值"DENY"
    security_x_frame_options: str = Field(default=DEFAULT_X_FRAME_OPTIONS, alias="SECURITY_X_FRAME_OPTIONS")

    # security_referrer_policy: Referrer-Policy，使用默认值"no-referrer"
    security_referrer_policy: str = Field(default=DEFAULT_REFERRER_POLICY, alias="SECURITY_REFERRER_POLICY")

    # security_permissions_policy: Permissions-Policy，使用默认值（禁止地理位置、麦克风、摄像头）
    security_permissions_policy: str = Field(default=DEFAULT_PERMISSIONS_POLICY, alias="SECURITY_PERMISSIONS_POLICY")

    # CORS配置
    # cors_allow_origins: 允许的源，默认"*"（所有源）
    cors_allow_origins: str = Field(default="*", alias="CORS_ALLOW_ORIGINS")

    # cors_allow_credentials: 是否允许携带凭证（cookies），默认False
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")

    # cors_allow_methods: 允许的HTTP方法，默认常用方法
    cors_allow_methods: str = Field(default="GET,POST,PUT,PATCH,DELETE,OPTIONS", alias="CORS_ALLOW_METHODS")

    # cors_allow_headers: 允许的请求头，默认Authorization、Content-Type、X-Request-Id
    cors_allow_headers: str = Field(default="Authorization,Content-Type,X-Request-Id", alias="CORS_ALLOW_HEADERS")

    # 限流配置
    # rate_limit_enabled: 是否启用限流，默认True
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    # auth_rate_limit_per_window: 每个时间窗口内允许的认证请求数，默认20
    auth_rate_limit_per_window: int = Field(default=20, alias="AUTH_RATE_LIMIT_PER_WINDOW")

    # auth_rate_limit_window_seconds: 限流时间窗口（秒），默认60
    auth_rate_limit_window_seconds: int = Field(default=60, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")

    # 使用model_validator装饰器定义模型级别验证器
    # mode="after" 表示在字段验证之后执行
    @model_validator(mode="after")
    def _validate_cors(self) -> "Settings":
        """
        验证CORS配置的合理性

        规则: 当CORS_ALLOW_ORIGINS为"*"时，CORS_ALLOW_CREDENTIALS不能为True
        因为浏览器不允许在允许所有源的情况下发送凭证（cookies）

        返回:
            self: 验证通过后返回自身
        """
        # 检查是否同时满足：允许所有源 且 允许携带凭证
        if (self.cors_allow_origins or "").strip() == "*" and bool(self.cors_allow_credentials):
            # 如果违反规则，抛出ValueError异常
            raise ValueError("CORS_ALLOW_CREDENTIALS cannot be true when CORS_ALLOW_ORIGINS is '*'.")
        # 验证通过，返回self
        return self

    # 定义静态方法_csv，用于解析逗号分隔的字符串为列表
    # 静态方法不需要访问实例属性，所以用@staticmethod装饰器
    @staticmethod
    def _csv(s: str) -> list[str]:
        """
        将逗号分隔的字符串解析为字符串列表

        参数:
            s: 逗号分隔的字符串，如 "GET,POST,PUT"

        返回:
            解析后的字符串列表，如 ["GET", "POST", "PUT"]
        """
        # 处理空值：如果s是None或空字符串，去掉空格后就是空字符串
        s = (s or "").strip()
        # 如果处理后是空字符串，返回空列表
        if not s:
            return []
        # 用逗号分割字符串，并去掉每个元素的首尾空格
        # 过滤掉空字符串（比如 "a,,b" 这种情况）
        return [x.strip() for x in s.split(",") if x.strip()]

    # 定义cors_origins_list方法，获取CORS允许的源列表
    def cors_origins_list(self) -> list[str]:
        """
        获取CORS允许的源列表

        返回:
            源列表，如果是"*"则返回["*"]，否则解析逗号分隔的字符串
        """
        # 如果配置是"*"，直接返回["*"]
        if (self.cors_allow_origins or "").strip() == "*":
            return ["*"]
        # 否则调用_csv方法解析逗号分隔的字符串
        return self._csv(self.cors_allow_origins)

    # 定义cors_methods_list方法，获取CORS允许的HTTP方法列表
    def cors_methods_list(self) -> list[str]:
        """
        获取CORS允许的HTTP方法列表

        返回:
            方法列表，如果解析结果为空则返回["*"]
        """
        # 调用_csv方法解析逗号分隔的字符串
        # 如果结果为空列表，则返回["*"]表示允许所有方法
        return self._csv(self.cors_allow_methods) or ["*"]

    # 定义cors_headers_list方法，获取CORS允许的请求头列表
    def cors_headers_list(self) -> list[str]:
        """
        获取CORS允许的请求头列表

        返回:
            请求头列表，如果解析结果为空则返回["*"]
        """
        # 调用_csv方法解析逗号分隔的字符串
        # 如果结果为空列表，则返回["*"]表示允许所有头
        return self._csv(self.cors_allow_headers) or ["*"]


# 创建Settings的单例实例
# 这样在其他模块中导入settings就可以直接使用，不需要重复创建
settings = Settings()