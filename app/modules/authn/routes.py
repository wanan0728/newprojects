# 6.5 app/modules/authn/routes.py
# 认证模块路由定义
#
# 这个文件定义了所有与认证相关的API路由，包括：
# - 注册 (/auth/register)
# - 登录 (/auth/login)
# - 刷新令牌 (/auth/refresh)
# - 登出 (/auth/logout)
# - 获取当前用户信息 (/auth/me)
#
# 每个接口都配置了适当的限流、审计日志和响应格式。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi导入APIRouter、Depends、Response
# APIRouter: 用于创建路由分组，可以把相关接口放在一起
# Depends: 用于依赖注入，可以在处理请求前执行一些代码（如获取数据库连接）
# Response: 用于设置响应头，比如设置no-store禁止缓存
from fastapi import APIRouter, Depends, Response

# 从sqlalchemy导入select，用于构建数据库查询语句
from sqlalchemy import select
# 从sqlalchemy.ext.asyncio导入AsyncSession，异步数据库会话
# 用于执行异步数据库操作，不会阻塞事件循环
from sqlalchemy.ext.asyncio import AsyncSession

# 从限流中间件导入限流相关组件
from app.api.middleware.rate_limit import RateLimitSpec, rate_limit_ip
# RateLimitSpec: 限流规则的数据类，包含名称、限制次数、时间窗口
# rate_limit_ip: 基于IP地址的限流依赖函数

# 从响应模块导入ok_no_store，用于返回不缓存的成功响应
# 这个函数会返回 {"data": ...} 格式的响应，并设置Cache-Control: no-store头
from app.api.response import ok_no_store

# 从API模式模块导入响应模型
from app.core.api_schemas import ActionResult, ApiResponse
# ActionResult: 操作结果模型，包含ok字段表示成功
# ApiResponse: 通用响应模型，包装data字段

# 从配置模块导入settings
# settings包含了所有应用配置，如JWT密钥、过期时间等
from app.core.config import settings

# 从错误处理模块导入抛出异常的函数
# raise_err会创建一个AppError异常并抛出，由全局异常处理器处理
from app.core.errors import raise_err

# 从数据库依赖导入get_db
# get_db是一个FastAPI依赖，用于获取数据库会话
from app.infra.db.deps import get_db

# 从Redis客户端导入get_redis
# get_redis是一个FastAPI依赖，用于获取Redis客户端
from app.infra.redis_client import get_redis

# 从审计钩子导入record
# record是审计日志的记录函数，会在整个项目中调用
from app.modules.audit.hook import record

# 从认证模块导入User模型
# User是用户表的数据库模型
from app.modules.auth.models import User

# 从认证模块导入常量
from app.modules.authn.consts import RL_AUTH_LOGIN, RL_AUTH_REFRESH, RL_AUTH_REGISTER
# RL_AUTH_REGISTER: 注册接口限流规则名称
# RL_AUTH_LOGIN: 登录接口限流规则名称
# RL_AUTH_REFRESH: 刷新接口限流规则名称

# 从认证依赖导入get_current_user
# get_current_user是获取当前登录用户的依赖，会验证token并返回User对象
from app.modules.authn.deps import get_current_user

# 从认证模式导入请求/响应模型
from app.modules.authn.schemas import LoginReq, MeResp, RefreshReq, RegisterReq, TokenResp
# LoginReq: 登录请求体，包含email和password
# MeResp: 用户信息响应，包含id、email、状态等
# RefreshReq: 刷新请求体，包含refresh_token
# RegisterReq: 注册请求体，包含email和password
# TokenResp: 令牌响应，包含access_token和refresh_token

# 从认证服务导入所有工具函数
from app.modules.authn.service import (
    bump_tokenver,           # 增加令牌版本（使旧令牌失效）
    get_tokenver,            # 获取当前令牌版本
    mint_refresh_token,      # 生成新的刷新令牌
    pack_refresh,            # 打包刷新令牌（rid + secret）
    revoke_refresh,          # 撤销刷新令牌
    store_refresh,           # 存储刷新令牌到Redis
    unpack_refresh,          # 解析刷新令牌
    verify_and_consume_refresh,  # 验证并消费刷新令牌
)

# 从JWT模块导入创建访问令牌的函数
from app.modules.security.jwt import create_access_token

# 从密码模块导入密码哈希和验证函数
from app.modules.security.password import hash_password, verify_password

# 创建APIRouter实例，所有认证路由都加上/auth前缀
# prefix="/auth" 表示所有路由的URL都以/auth开头
# tags=["auth"] 表示在API文档中这些路由归在"auth"标签下
router = APIRouter(prefix="/auth", tags=["auth"])


# 定义_noop_dep空操作依赖函数
# 当限流关闭时，用这个空依赖替代限流依赖，保持routes写法不变。
async def _noop_dep() -> None:
    """空操作依赖，当限流关闭时使用"""
    # 这个函数什么都不做，只是返回None
    # 因为限流关闭时，我们不需要任何限流逻辑
    return None


# 定义_auth_rl函数，生成按IP限流的依赖函数
# name: str 限流规则名称，用来区分不同接口的限流桶
# -> 返回一个FastAPI依赖函数
def _auth_rl(name: str):
    """生成按IP限流的依赖函数"""
    # 如果限流功能被禁用，返回空操作依赖
    # settings.rate_limit_enabled 从配置中读取是否启用限流
    if not settings.rate_limit_enabled:
        return _noop_dep

    # 返回按IP限流的依赖
    # rate_limit_ip函数会返回一个FastAPI依赖
    return rate_limit_ip(  # 返回一个Depends依赖，用来固定窗口计数，超过抛429
        RateLimitSpec(
            name=name,                                         # 限流规则名称
            limit=settings.auth_rate_limit_per_window,        # 时间窗口内允许的请求次数
            window_seconds=settings.auth_rate_limit_window_seconds,  # 时间窗口（秒）
        )
    )


# 创建不同接口的限流依赖
# 调用_auth_rl函数，传入对应的限流规则名称
# 如果限流启用，这些变量就是真正的限流依赖；如果禁用，就是_noop_dep
_rl_register = _auth_rl(RL_AUTH_REGISTER)  # 注册接口限流依赖
_rl_login = _auth_rl(RL_AUTH_LOGIN)        # 登录接口限流依赖
_rl_refresh = _auth_rl(RL_AUTH_REFRESH)    # 刷新接口限流依赖


# 使用@router.post装饰器定义POST请求的路由
# "/register" 是路由路径，完整路径是 /auth/register
# response_model=ApiResponse[MeResp] 指定响应模型，Swagger会自动生成文档
# status_code=201 表示成功时返回201 Created状态码
# dependencies=[Depends(_rl_register)] 表示这个路由会应用限流依赖
@router.post(
    "/register",
    response_model=ApiResponse[MeResp],  # 响应模型：包装在ApiResponse中的MeResp
    status_code=201,                      # 成功时返回201 Created
    dependencies=[Depends(_rl_register)], # 应用注册限流
)
# 定义register异步函数，处理注册请求
# req: RegisterReq 请求体，FastAPI会自动解析JSON并验证
# response: Response 响应对象，用于设置响应头
# db: AsyncSession 数据库会话，从get_db依赖获取
async def register(req: RegisterReq, response: Response, db: AsyncSession = Depends(get_db)):
    """
    用户注册接口

    参数:
        req: 注册请求体，包含email和password
        response: 响应对象，用于设置no-store头
        db: 数据库会话

    返回:
        新创建的用户信息
    """
    # 使用事务，确保操作的原子性
    # async with db.begin() 会开始一个事务，如果块内代码执行成功，自动提交
    # 如果抛出异常，自动回滚
    async with db.begin():  # 事务打开
        # 检查邮箱是否已被注册
        # select(User).where(User.email == req.email) 构建查询
        # db.execute() 执行查询
        # scalar_one_or_none() 返回单个结果，如果没有返回None，如果有多个抛异常
        exists = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()  # 根据结果数量返回不同内容
        if exists:  # 如果邮箱已存在
            # 邮箱已被占用，记录审计日志并抛出异常
            record(
                action="auth.register",      # 操作名称
                status="deny",                # 状态：拒绝
                http_status=409,              # HTTP状态码：409 Conflict
                meta={"reason": "email_taken", "email": str(req.email)},  # 元数据
            )
            raise_err("auth.email_taken")    # 抛出错误码为email_taken的异常

        # 创建新用户
        # User(email=..., password_hash=...) 创建User对象
        # hash_password(req.password) 对密码进行哈希加密
        user = User(email=req.email, password_hash=hash_password(req.password))
        db.add(user)  # 将新用户对象添加到数据库会话中

        # 刷新session，生成数据库自增ID
        # flush() 会将数据发送到数据库，但不提交事务
        # 这样user.id就会被数据库生成
        await db.flush()  # 将更改发送到数据库，生成user.id
        # refresh() 从数据库重新加载数据，确保user对象包含所有数据库生成的字段
        await db.refresh(user)  # 从数据库重新加载用户对象，填充自动生成的字段（如id、created_at等）

    # 事务块结束，自动提交

    # 记录注册成功的审计日志
    record(
        action="auth.register",
        status="ok",
        actor_user_id=int(user.id),          # 操作者用户ID
        meta={"user_id": int(user.id), "email": str(user.email)},
    )

    # 构建响应数据
    data = MeResp(
        id=int(user.id),                     # 用户ID
        email=user.email,                    # 用户邮箱
        is_active=bool(user.is_active),       # 确保是布尔值（是否激活）
        is_superadmin=bool(user.is_superadmin),  # 确保是布尔值（是否为超级管理员）
    )

    # 返回成功响应，并设置no-store头
    # ok_no_store会调用ok函数包装数据，并设置Cache-Control: no-store
    return ok_no_store(response, data)


# 定义登录接口
@router.post(
    "/login",
    response_model=ApiResponse[TokenResp],
    dependencies=[Depends(_rl_login)],  # 应用登录限流
)
async def login(
        req: LoginReq,
        response: Response,
        db: AsyncSession = Depends(get_db),
        redis=Depends(get_redis),
):
    """
    用户登录接口

    参数:
        req: 登录请求体，包含email和password
        response: 响应对象
        db: 数据库会话
        redis: Redis客户端

    返回:
        包含access_token和refresh_token的响应
    """
    # 根据邮箱查询用户
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()

    # 检查用户是否存在且激活
    if not user or not bool(user.is_active):  # 如果用户不存在或未激活
        record(action="auth.login", status="deny", http_status=401, meta={"email": str(req.email)})
        raise_err("auth.credentials_invalid")  # 抛出凭证无效错误

    # 验证密码
    if not verify_password(req.password, user.password_hash):  # 如果密码错误
        record(action="auth.login", status="deny", http_status=401, meta={"email": str(req.email)})
        raise_err("auth.credentials_invalid")  # 抛出凭证无效错误

    # 增加令牌版本，使该用户的所有旧访问令牌立即失效（全端踢下线）
    # bump_tokenver 会在Redis中增加用户的令牌版本号
    token_ver = await bump_tokenver(redis, int(user.id))  # token version自增，让所有旧的access token立即失效
    token_ver = int(token_ver)  # 确保是整数

    # 生成新的访问令牌（短期）
    access = create_access_token(  # 生成短期访问令牌
        secret=settings.jwt_secret,                    # JWT密钥
        issuer=settings.jwt_issuer,                    # 签发者
        alg=settings.jwt_alg.value,                    # 加密算法
        user_id=int(user.id),                           # 用户ID
        token_ver=int(token_ver),                       # 当前令牌版本
        minutes=settings.access_token_expire_minutes,   # 过期分钟数
    )

    # 生成新的刷新令牌
    pair = mint_refresh_token()  # 这里生成刷新令牌（包含rid和secret）

    # 将刷新令牌存储到Redis
    await store_refresh(  # 然后将刷新令牌存入redis，存入的是user_id|token_ver|sha256(secret)这个东西
        redis,
        pair=pair,                                   # 刷新令牌对
        user_id=int(user.id),                         # 用户ID
        token_ver=int(token_ver),                     # 当前令牌版本
        ttl_days=settings.refresh_token_expire_days,  # 过期天数
    )

    # 记录登录成功的审计日志
    record(action="auth.login", status="ok", actor_user_id=int(user.id), meta={"user_id": int(user.id)})

    # 构建响应数据
    data = TokenResp(  # 返回access和refresh
        access_token=access,                                  # 访问令牌
        expires_in_minutes=settings.access_token_expire_minutes,  # 过期时间
        refresh_token=pack_refresh(pair),                     # 打包后的刷新令牌
    )

    # 返回成功响应
    return ok_no_store(response, data)


# 定义刷新令牌接口
# 刷新，主要是refresh token校验和消费一次性完成，然后颁发新的access和新的refresh
@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResp],
    dependencies=[Depends(_rl_refresh)],  # 应用刷新限流
)
async def refresh(
        req: RefreshReq,
        response: Response,
        db: AsyncSession = Depends(get_db),
        redis=Depends(get_redis),
):
    """
    刷新令牌接口

    参数:
        req: 刷新请求体，包含refresh_token
        response: 响应对象
        db: 数据库会话
        redis: Redis客户端

    返回:
        新的access_token和refresh_token
    """
    # 解析客户端传入的刷新令牌
    try:
        # unpack_refresh 会将 "rid.secret" 格式的字符串解析成 RefreshTokenPair 对象
        pair = unpack_refresh(req.refresh_token)
    except Exception:  # 如果解析过程中发生任何异常
        # 解析失败，格式错误
        record(action="auth.refresh", status="deny", http_status=401, meta={"reason": "bad_format"})
        raise_err("auth.refresh_token_invalid")

    # 验证并消费刷新令牌（原子操作，使用Lua脚本）
    consumed = await verify_and_consume_refresh(redis, pair=pair)
    # redis lua脚本，主要是校验secret_hash匹配后在删除rid，主打一次性消费
    if not consumed:  # 如果验证失败（返回None）
        # 验证失败（令牌不存在或不匹配）
        record(action="auth.refresh", status="deny", http_status=401, meta={"reason": "not_found_or_mismatch"})
        raise_err("auth.refresh_token_invalid")

    # 从Redis中取出用户ID和令牌版本
    # consumed 是 (user_id, token_ver) 元组
    user_id, token_ver = consumed  # 从redis值里取出user_id和token_ver

    # 再次读取当前tokenver，确保refresh对应的版本仍有效
    current_ver = await get_tokenver(redis, int(user_id))  # 从Redis中获取当前用户的令牌版本号
    if int(token_ver) != int(current_ver):  # 如果刷新令牌携带的版本号与当前版本号不一致
        # 版本不匹配，说明令牌已被吊销（用户可能修改了密码或登出）
        record(
            action="auth.refresh",                          # 记录刷新操作
            status="deny",                                   # 操作被拒绝
            http_status=401,                                 # HTTP状态码401 Unauthorized
            meta={"reason": "tokenver_mismatch", "user_id": int(user_id)},  # 附加信息：版本不匹配、用户ID
        )
        raise_err("auth.refresh_token_expired")             # 抛出刷新令牌过期异常

    # 查询用户，确保用户仍存在且激活
    # 执行数据库查询：SELECT * FROM users WHERE id = :user_id
    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()  # 获取用户对象或None
    # 读取用户实体，避免refresh对应用户被禁用仍能换新token
    if not user or not bool(user.is_active):  # 如果用户不存在或账户未激活
        record(
            action="auth.refresh",                          # 记录刷新操作
            status="deny",                                   # 操作被拒绝
            http_status=401,                                 # HTTP状态码401
            meta={"reason": "user_inactive", "user_id": int(user_id)},  # 附加信息：用户未激活
        )
        raise_err("auth.user_inactive")                     # 抛出用户未激活异常

    # 生成新的访问令牌
    access = create_access_token(  # 生成新的access token
        secret=settings.jwt_secret,                         # JWT签名密钥
        issuer=settings.jwt_issuer,                         # 签发者
        alg=settings.jwt_alg.value,                         # 加密算法
        user_id=int(user_id),                                # 用户ID
        token_ver=int(token_ver),                            # 当前令牌版本
        minutes=settings.access_token_expire_minutes,       # 过期时间（分钟）
    )

    # 生成新的刷新令牌（每次刷新都生成新的）
    new_pair = mint_refresh_token()  # 生成新的refresh，一次刷新发一次新refresh

    # 存储新的刷新令牌
    await store_refresh(  # 将新的刷新令牌存入Redis
        redis,                                              # Redis客户端
        pair=new_pair,                                      # 新的刷新令牌对
        user_id=int(user_id),                                # 用户ID
        token_ver=int(token_ver),                            # 当前令牌版本
        ttl_days=settings.refresh_token_expire_days,        # 过期天数
    )

    # 记录刷新成功的审计日志
    record(
        action="auth.refresh",                               # 操作名称
        status="ok",                                         # 状态成功
        actor_user_id=int(user_id),                          # 操作者用户ID
        meta={"user_id": int(user_id)}                       # 附加信息
    )

    # 构建响应数据
    data = TokenResp(  # 返回新的access + refresh
        access_token=access,                                  # 新的访问令牌
        expires_in_minutes=settings.access_token_expire_minutes,  # 过期时间
        refresh_token=pack_refresh(new_pair),                # 打包后的新刷新令牌
    )

    # 返回成功响应
    return ok_no_store(response, data)                       # 返回不缓存的成功响应


# 定义登出接口
# 注销，这里尽量撤销当前refresh，并bump tokenver让所有旧access失效
@router.post("/logout", response_model=ApiResponse[ActionResult])  # 响应模型为ActionResult
async def logout(
        req: RefreshReq,                                       # 登出请求体，包含refresh_token
        response: Response,                                   # 响应对象
        redis=Depends(get_redis),                             # Redis客户端依赖
        me: User = Depends(get_current_user),                 # 依赖get_current_user，先验证用户身份
):
    """
    用户登出接口

    参数:
        req: 登出请求体，包含refresh_token
        response: 响应对象
        redis: Redis客户端
        me: 当前登录用户（从get_current_user获取）

    返回:
        操作结果
    """
    # 尝试撤销传入的刷新令牌
    try:
        pair = unpack_refresh(req.refresh_token)  # 解析刷新令牌，得到rid和secret
        await revoke_refresh(redis, pair.rid)     # 删除Redis中对应rid的key，撤销该刷新令牌
    except Exception:  # 如果解析或撤销失败（例如令牌格式错误）
        pass  # 登出尽量幂等，refresh不对也不影响继续登出流程

    # 增加令牌版本，使所有旧访问令牌失效
    await bump_tokenver(redis, int(me.id))  # tokenver自增，这样该用户所有旧access token立即失效

    # 记录登出成功的审计日志
    record(
        action="auth.logout",                                 # 操作名称
        status="ok",                                          # 状态成功
        meta={"user_id": int(me.id)}                          # 附加信息：用户ID
    )

    # 返回成功响应
    return ok_no_store(response, ActionResult(ok=True))  # 返回ActionResult，ok=True表示成功


# 定义获取当前用户信息接口
@router.get("/me", response_model=ApiResponse[MeResp])       # 响应模型为ApiResponse[MeResp]
async def me(response: Response, user: User = Depends(get_current_user)):
    """
    获取当前用户信息接口

    参数:
        response: 响应对象
        user: 当前登录用户（从get_current_user获取）

    返回:
        当前用户的信息
    """
    # 记录审计日志
    record(
        action="auth.me",                                     # 操作名称
        status="ok",                                          # 状态成功
        meta={"user_id": int(user.id)}                        # 附加信息：用户ID
    )

    # 构建响应数据
    data = MeResp(
        id=int(user.id),                                      # 用户ID
        email=user.email,                                     # 用户邮箱
        is_active=bool(user.is_active),                       # 是否激活
        is_superadmin=bool(user.is_superadmin),               # 是否为超级管理员
    )

    # 返回成功响应
    return ok_no_store(response, data)                        # 返回不缓存的用户信息