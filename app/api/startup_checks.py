# 4.6 app/api/startup_checks.py
# 启动前检查模块
#
# 这段代码在项目启动之前作为一次性的检测脚本，只运行一次，通过了项目就可以启动了。
# 它的作用是在应用完全启动前，检查所有必要的配置和依赖服务是否就绪，
# 避免应用启动后因配置错误或服务不可用而导致运行时错误。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入logging模块，用于记录警告日志
import logging

# 从sqlalchemy导入text，用于执行原生SQL语句
from sqlalchemy import text

# 从配置模块导入settings，获取应用配置
from app.core.config import settings
# 从枚举模块导入Env，用于判断环境类型
from app.core.enums import Env

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 定义_is_prod函数，判断当前是否是生产环境
# -> bool 返回布尔值：True表示生产环境，False表示非生产环境
def _is_prod() -> bool:
    """
    判断当前环境是否为生产环境

    返回:
        True: 是生产环境（prod或production）
        False: 不是生产环境（dev、staging等）
    """
    # 是不是生产环境/上线了
    # 检查settings.env是否在{Env.prod, Env.production}集合中
    return settings.env in {Env.prod, Env.production}


# 定义run_startup_checks异步函数，执行启动前检查
# app 参数，FastAPI应用实例
async def run_startup_checks(app) -> None:
    """
    执行启动前检查

    检查项包括：
    1. JWT密钥强度
    2. CORS配置合理性
    3. Redis连接
    4. 数据库连接
    5. Elasticsearch连接

    在生产环境中，检查失败会抛出异常，阻止应用启动。
    在非生产环境中，检查失败只会记录警告，允许应用继续启动。
    """
    # 判断当前是否为生产环境
    prod = _is_prod()

    # === 检查1：JWT密钥强度 ===
    # 检查jwt_secret是否存在且长度至少32位
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        # 准备警告消息和额外信息
        msg = "weak_jwt_secret"  # JWT密钥太弱
        extra = {"min_len": 32, "env": str(settings.env)}  # 最小长度要求32，当前环境

        if prod:
            # 生产环境：抛出异常，阻止启动
            raise RuntimeError(f"{msg}: {extra}")
        # 非生产环境：只记录警告，允许启动
        logger.warning(msg, extra=extra)

    # === 检查2：CORS配置合理性 ===
    # 检查是否同时允许所有源(*)和允许携带凭证(credentials)
    # 这种组合是不安全的，浏览器也会拒绝
    if settings.cors_allow_credentials and (settings.cors_allow_origins or "").strip() == "*":
        msg = "cors_invalid_credentials_with_wildcard_origin"  # CORS配置无效：通配符源不能携带凭证
        extra = {"env": str(settings.env)}

        if prod:
            # 生产环境：抛出异常，阻止启动
            raise RuntimeError(f"{msg}: {extra}")
        # 非生产环境：只记录警告
        logger.warning(msg, extra=extra)

    # === 检查3：Redis连接 ===
    # 执行Redis ping命令，测试连接
    await app.state.redis.ping()
    # 如果ping失败，会抛出异常

    # === 检查4：数据库连接 ===
    # 从应用状态中获取数据库会话工厂
    session_maker = app.state.db_session_maker
    # 创建会话
    async with session_maker() as session:
        # 执行简单的SELECT 1，测试数据库连接
        await session.execute(text("SELECT 1"))
    # 如果执行失败，会抛出异常

    # === 检查5：Elasticsearch连接 ===
    # 执行ES ping，测试连接
    ok = await app.state.es.ping()
    if not ok:
        # 如果ping返回False，说明ES连接失败
        # 无论是生产还是非生产环境，ES连接失败都抛出异常
        # 因为ES可能是核心依赖
        raise RuntimeError("elasticsearch_ping_failed")