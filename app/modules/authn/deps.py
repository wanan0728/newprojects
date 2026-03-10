# 6.4 app/modules/authn/deps.py
# 认证模块依赖项
#
# 这个文件定义了FastAPI依赖项，用于在请求中获取当前登录用户。
# 主要功能包括：解析Bearer Token、验证令牌有效性、检查用户状态、
# 记录审计日志等。所有需要用户认证的接口都可以依赖get_current_user。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi导入Depends，用于创建依赖项
# Depends 是 FastAPI 的依赖注入系统核心，可以将函数标记为依赖项
from fastapi import Depends

# 从fastapi.security导入HTTPBearer和HTTPAuthorizationCredentials
# HTTPBearer: Bearer Token认证的解析器，用于从Authorization头中提取token
# HTTPAuthorizationCredentials: 认证凭证对象，包含token信息和schema（如"Bearer"）
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# 从sqlalchemy导入select，用于构建查询语句
# select 是 SQLAlchemy 的查询构造器，可以生成 SELECT 语句
from sqlalchemy import select
# 从sqlalchemy.ext.asyncio导入AsyncSession，异步数据库会话
# AsyncSession 用于执行异步数据库操作，不会阻塞事件循环
from sqlalchemy.ext.asyncio import AsyncSession

# 从配置模块导入settings，获取JWT配置（如密钥、签发者、算法）
from app.core.config import settings
# 从错误处理模块导入抛出异常的函数
# raise_err 会创建一个 AppError 异常并抛出，由全局异常处理器处理
from app.core.errors import raise_err
# 从请求上下文模块导入设置用户ID的函数
# set_user_id 用于将用户ID存储到当前请求的上下文变量中，供审计等使用
from app.core.request_context import set_user_id
# 从数据库依赖模块导入获取数据库会话的依赖
# get_db 是一个 FastAPI 依赖，用于获取异步数据库会话
from app.infra.db.deps import get_db
# 从Redis客户端模块导入获取Redis连接的依赖
# get_redis 是一个 FastAPI 依赖，用于获取 Redis 客户端
from app.infra.redis_client import get_redis
# 从审计钩子模块导入记录审计事件的函数
# record 用于记录审计日志，会在整个项目中调用
from app.modules.audit.hook import record
# 从认证模块导入User模型
# User 是用户表的 SQLAlchemy 模型类
from app.modules.auth.models import User
# 从认证服务模块导入获取令牌版本的函数
# get_tokenver 用于从 Redis 中获取指定用户的当前令牌版本号
from app.modules.authn.service import get_tokenver
# 从JWT模块导入解码访问令牌的函数
# decode_access_token 用于解码并验证 JWT 令牌，返回 TokenPayload 对象
from app.modules.security.jwt import decode_access_token

# 创建HTTPBearer实例，用于从请求头中提取Bearer Token
# auto_error=False 表示没有token时不自动抛403，由我们自己手工处理
# 这样我们可以返回自定义的错误信息，而不是默认的 403 响应
bearer_scheme = HTTPBearer(auto_error=False)


# 定义get_current_user异步函数，获取当前登录用户
# creds: HTTPAuthorizationCredentials | None 从请求头中解析的认证凭证
# db: AsyncSession 数据库会话，从get_db依赖获取
# redis: Redis客户端，从get_redis依赖获取
# -> User 返回User对象
async def get_current_user(
        creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
        redis=Depends(get_redis),
) -> User:
    """
    获取当前登录用户

    这个依赖项会：
    1. 从请求头中提取Bearer Token
    2. 解码并验证JWT令牌
    3. 检查令牌版本是否匹配（防止旧令牌继续使用）
    4. 从数据库查询用户信息
    5. 检查用户是否激活
    6. 设置用户ID到请求上下文
    7. 返回用户对象

    如果任何步骤失败，会记录审计日志并抛出相应的异常。
    """

    # === 步骤1：检查是否提供了Bearer Token ===
    # creds为None表示没有Authorization头
    # creds.credentials为空表示有头但没值
    if creds is None or not creds.credentials:  # 如果没有凭证或凭证内容为空
        # 记录审计日志：缺少Bearer Token
        record(
            action="auth.bearer_required",  # 操作：需要Bearer Token
            status="deny",  # 状态：拒绝
            http_status=401,  # HTTP状态码：401 Unauthorized
            meta={"where": "get_current_user"}  # 元数据：哪里发生的
        )
        # 抛出异常：缺少Bearer Token
        raise_err("auth.bearer_required")  # 使用预定义的错误码抛出异常

    # 获取令牌字符串
    token = creds.credentials  # 从凭证对象中提取 token 字符串

    # === 步骤2：解码并验证JWT令牌 ===
    try:
        # 调用decode_access_token解码令牌
        payload = decode_access_token(
            token=token,  # JWT字符串
            secret=settings.jwt_secret,  # JWT密钥
            issuer=settings.jwt_issuer,  # 预期的签发者
            alg=settings.jwt_alg.value,  # 加密算法（如HS256）
        )
    except ValueError:  # 如果解码失败（签名错误、过期、格式错误等）
        # 解码失败（签名错误、过期、格式错误等）
        record(
            action="auth.access_token_invalid",  # 操作：访问令牌无效
            status="deny",  # 状态：拒绝
            http_status=401,  # HTTP状态码：401
            meta={"where": "get_current_user"}  # 元数据：哪里发生的
        )
        raise_err("auth.access_token_invalid")  # 抛出访问令牌无效异常

    # === 步骤3：验证令牌版本 ===
    # 从Redis获取当前用户的令牌版本
    current_ver = await get_tokenver(redis, payload.user_id)  # 调用服务函数获取版本号

    # 比较令牌中的版本和Redis中的版本
    if int(payload.token_ver) != int(current_ver):  # 如果不相等
        # 版本不匹配，说明令牌已被吊销（用户修改密码或登出）
        record(
            action="auth.access_token_expired",  # 操作：访问令牌过期
            status="deny",  # 状态：拒绝
            http_status=401,  # HTTP状态码：401
            meta={  # 元数据
                "where": "get_current_user",
                "user_id": int(payload.user_id)  # 记录用户ID方便追踪
            },
        )
        raise_err("auth.access_token_expired")  # 抛出令牌过期异常

    # === 步骤4：从数据库查询用户 ===
    # 构建查询：SELECT * FROM users WHERE id = :user_id
    stmt = select(User).where(User.id == payload.user_id)  # 创建查询语句

    # 执行查询，scalar_one_or_none() 返回单个结果或None
    user = (await db.execute(stmt)).scalar_one_or_none()  # 从数据库获取用户对象

    # === 步骤5：检查用户是否存在且激活 ===
    if not user or not bool(user.is_active):  # 如果用户不存在或未激活
        # 用户不存在或被禁用
        record(
            action="auth.user_inactive",  # 操作：用户未激活
            status="deny",  # 状态：拒绝
            http_status=401,  # HTTP状态码：401
            meta={  # 元数据
                "where": "get_current_user",
                "user_id": int(payload.user_id)  # 记录用户ID
            },
        )
        raise_err("auth.user_inactive")  # 抛出用户未激活异常

    # === 步骤6：设置用户ID到请求上下文 ===
    # 这样审计日志、其他中间件就可以获取当前用户ID
    set_user_id(int(user.id))  # 将用户ID存储到上下文变量中

    # === 步骤7：返回用户对象 ===
    # 依赖项会把这个对象注入到路径函数中
    return user  # 返回用户对象，供路径操作函数使用