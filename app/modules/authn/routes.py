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
# APIRouter: 用于创建路由分组
# Depends: 用于依赖注入
# Response: 用于设置响应头
from fastapi import APIRouter, Depends, Response

# 从sqlalchemy导入select，用于构建查询
from sqlalchemy import select
# 从sqlalchemy.ext.asyncio导入AsyncSession，异步数据库会话
from sqlalchemy.ext.asyncio import AsyncSession

# 从限流中间件导入限流相关组件
from app.api.middleware.rate_limit import RateLimitSpec, rate_limit_ip

# 从响应模块导入ok_no_store，用于返回不缓存的成功响应
from app.api.response import ok_no_store

# 从API模式模块导入响应模型
from app.core.api_schemas import ActionResult, ApiResponse
# 从配置模块导入settings
from app.core.config import settings
# 从错误处理模块导入抛出异常的函数
from app.core.errors import raise_err
# 从数据库依赖导入get_db
from app.infra.db.deps import get_db
# 从Redis客户端导入get_redis
from app.infra.redis_client import get_redis
# 从审计钩子导入record
from app.modules.audit.hook import record
# 从认证模块导入User模型
from app.modules.auth.models import User
# 从认证模块导入常量
from app.modules.authn.consts import RL_AUTH_LOGIN, RL_AUTH_REFRESH, RL_AUTH_REGISTER
# 从认证依赖导入get_current_user
from app.modules.authn.deps import get_current_user
# 从认证模式导入请求/响应模型
from app.modules.authn.schemas import LoginReq, MeResp, RefreshReq, RegisterReq, TokenResp
# 从认证服务导入所有工具函数
from app.modules.authn.service import (
    bump_tokenver,  # 增加令牌版本（使旧令牌失效）
    get_tokenver,  # 获取当前令牌版本
    mint_refresh_token,  # 生成新的刷新令牌
    pack_refresh,  # 打包刷新令牌（rid + secret）
    revoke_refresh,  # 撤销刷新令牌
    store_refresh,  # 存储刷新令牌到Redis
    unpack_refresh,  # 解析刷新令牌
    verify_and_consume_refresh,  # 验证并消费刷新令牌
)
# 从JWT模块导入创建访问令牌的函数
from app.modules.security.jwt import create_access_token
# 从密码模块导入密码哈希和验证函数
from app.modules.security.password import hash_password, verify_password

# 创建APIRouter实例，所有认证路由都加上/auth前缀
router = APIRouter(prefix="/auth", tags=["auth"])


# 定义_noop_dep空操作依赖函数
# 当限流关闭时，用这个空依赖替代限流依赖，保持routes写法不变。
async def _noop_dep() -> None:
    """空操作依赖，当限流关闭时使用"""
    return None


# 定义_auth_rl函数，生成按IP限流的依赖函数
# name: str 限流规则名称，用来区分不同接口的限流桶
# -> 返回一个FastAPI依赖函数
def _auth_rl(name: str):
    """生成按IP限流的依赖函数"""
    # 如果限流功能被禁用，返回空操作依赖
    if not settings.rate_limit_enabled:
        return _noop_dep

    # 返回按IP限流的依赖
    return rate_limit_ip(  # 返回一个Depends依赖，用来固定窗口计数，超过抛429
        RateLimitSpec(
            name=name,  # 限流规则名称
            limit=settings.auth_rate_limit_per_window,  # 时间窗口内允许的请求次数
            window_seconds=settings.auth_rate_limit_window_seconds,  # 时间窗口（秒）
        )
    )


# 创建不同接口的限流依赖
_rl_register = _auth_rl(RL_AUTH_REGISTER)  # 注册接口限流依赖
_rl_login = _auth_rl(RL_AUTH_LOGIN)  # 登录接口限流依赖
_rl_refresh = _auth_rl(RL_AUTH_REFRESH)  # 刷新接口限流依赖


@router.post(
    "/register",
    response_model=ApiResponse[MeResp],  # 响应模型：包装在ApiResponse中的MeResp
    status_code=201,  # 成功时返回201 Created
    dependencies=[Depends(_rl_register)],  # 应用注册限流
)
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
    async with db.begin():  # 事务打开
        # 检查邮箱是否已被注册
        exists = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()  # 根据结果数量返回不同内容
        if exists:
            # 邮箱已被占用，记录审计日志并抛出异常
            record(
                action="auth.register",
                status="deny",
                http_status=409,
                meta={"reason": "email_taken", "email": str(req.email)},
            )
            raise_err("auth.email_taken")

        # 创建新用户
        user = User(email=req.email, password_hash=hash_password(req.password))
        db.add(user)  # 加入session

        # 刷新session，生成数据库自增ID
        await db.flush()  # user.id生成postgres的identity或者sequence
        await db.refresh(user)  # refresh把数据库生成字段回填到orm对象

    # 记录注册成功的审计日志
    record(
        action="auth.register",
        status="ok",
        actor_user_id=int(user.id),
        meta={"user_id": int(user.id), "email": str(user.email)},
    )

    # 构建响应数据
    data = MeResp(
        id=int(user.id),
        email=user.email,
        is_active=bool(user.is_active),
        is_superadmin=bool(user.is_superadmin),
    )

    # 返回成功响应，并设置no-store头
    return ok_no_store(response, data)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResp],
    dependencies=[Depends(_rl_login)],
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
    if not user or not bool(user.is_active):
        record(action="auth.login", status="deny", http_status=401, meta={"email": str(req.email)})
        raise_err("auth.credentials_invalid")

    # 验证密码
    if not verify_password(req.password, user.password_hash):
        record(action="auth.login", status="deny", http_status=401, meta={"email": str(req.email)})
        raise_err("auth.credentials_invalid")

    # 增加令牌版本，使该用户的所有旧访问令牌立即失效（全端踢下线）
    token_ver = await bump_tokenver(redis, int(user.id))  # token version自增，让所有旧的access token立即失效，这里全端踢下线
    token_ver = int(token_ver)

    # 生成新的访问令牌（短期）
    access = create_access_token(  # 生成短期访问令牌
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        alg=settings.jwt_alg.value,
        user_id=int(user.id),
        token_ver=int(token_ver),
        minutes=settings.access_token_expire_minutes,
    )

    # 生成新的刷新令牌
    pair = mint_refresh_token()  # 这里生成刷新令牌

    # 将刷新令牌存储到Redis
    await store_refresh(  # 然后将刷新令牌存入redis，存入的是user_id|token_ver|sha256(secret)这个东西
        redis,
        pair=pair,
        user_id=int(user.id),
        token_ver=int(token_ver),
        ttl_days=settings.refresh_token_expire_days,
    )

    # 记录登录成功的审计日志
    record(action="auth.login", status="ok", actor_user_id=int(user.id), meta={"user_id": int(user.id)})

    # 构建响应数据
    data = TokenResp(  # 返回access和refresh
        access_token=access,
        expires_in_minutes=settings.access_token_expire_minutes,
        refresh_token=pack_refresh(pair),
    )

    # 返回成功响应
    return ok_no_store(response, data)


@router.post(  # 刷新，主要是refresh token校验和消费一次性完成，然后颁发新的access和新的refresh
    "/refresh",
    response_model=ApiResponse[TokenResp],
    dependencies=[Depends(_rl_refresh)],
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
        pair = unpack_refresh(req.refresh_token)
    except Exception:
        # 解析失败，格式错误
        record(action="auth.refresh", status="deny", http_status=401, meta={"reason": "bad_format"})
        raise_err("auth.refresh_token_invalid")

    # 验证并消费刷新令牌（原子操作，使用Lua脚本）
    consumed = await verify_and_consume_refresh(redis, pair=pair)
    # redis lua脚本，主要是校验secret_hash匹配后在删除rid，主打一次性消费
    if not consumed:
        # 验证失败（令牌不存在或不匹配）
        record(action="auth.refresh", status="deny", http_status=401, meta={"reason": "not_found_or_mismatch"})
        raise_err("auth.refresh_token_invalid")

    # 从Redis中取出用户ID和令牌版本
    user_id, token_ver = consumed  # 从redis值里取出user_id和token_ver

    # 再次读取当前tokenver，确保refresh对应的版本仍有效
    current_ver = await get_tokenver(redis, int(user_id))  # 再读取当前tokenver，确保refresh对应的版本仍有效
    if int(token_ver) != int(current_ver):
        # 版本不匹配，说明令牌已被吊销
        record(
            action="auth.refresh",
            status="deny",
            http_status=401,
            meta={"reason": "tokenver_mismatch", "user_id": int(user_id)},
        )
        raise_err("auth.refresh_token_expired")

    # 查询用户，确保用户仍存在且激活
    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    # 读取用户实体，避免refresh对应用户被禁用仍能换新token
    if not user or not bool(user.is_active):
        record(
            action="auth.refresh",
            status="deny",
            http_status=401,
            meta={"reason": "user_inactive", "user_id": int(user_id)},
        )
        raise_err("auth.user_inactive")

    # 生成新的访问令牌
    access = create_access_token(  # 生成新的access token
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        alg=settings.jwt_alg.value,
        user_id=int(user_id),
        token_ver=int(token_ver),
        minutes=settings.access_token_expire_minutes,
    )

    # 生成新的刷新令牌（每次刷新都生成新的）
    new_pair = mint_refresh_token()  # 生成新的refresh，一次刷新发一次新refresh

    # 存储新的刷新令牌
    await store_refresh(  # 生成新的refresh，一次刷新发一次新refresh
        redis,
        pair=new_pair,
        user_id=int(user_id),
        token_ver=int(token_ver),
        ttl_days=settings.refresh_token_expire_days,
    )

    # 记录刷新成功的审计日志
    record(action="auth.refresh", status="ok", actor_user_id=int(user_id), meta={"user_id": int(user_id)})

    # 构建响应数据
    data = TokenResp(  # 返回新的access + refresh
        access_token=access,
        expires_in_minutes=settings.access_token_expire_minutes,
        refresh_token=pack_refresh(new_pair),
    )

    # 返回成功响应
    return ok_no_store(response, data)


@router.post("/logout", response_model=ApiResponse[ActionResult])
# 注销，这里尽量撤销当前refresh），并bump tokenver让所有旧access失效
async def logout(
        req: RefreshReq,
        response: Response,
        redis=Depends(get_redis),
        me: User = Depends(get_current_user),
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
        pair = unpack_refresh(req.refresh_token)
        await revoke_refresh(redis, pair.rid)  # 删除对应rid的redis key
    except Exception:
        pass  # 登出尽量幂等，refresh不对也不影响继续登出流程

    # 增加令牌版本，使所有旧访问令牌失效
    await bump_tokenver(redis, int(me.id))  # tokenver自增，这样该用户所有旧access token立即失效

    # 记录登出成功的审计日志
    record(action="auth.logout", status="ok", meta={"user_id": int(me.id)})

    # 返回成功响应
    return ok_no_store(response, ActionResult(ok=True))


@router.get("/me", response_model=ApiResponse[MeResp])
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
    record(action="auth.me", status="ok", meta={"user_id": int(user.id)})

    # 构建响应数据
    data = MeResp(
        id=int(user.id),
        email=user.email,
        is_active=bool(user.is_active),
        is_superadmin=bool(user.is_superadmin),
    )

    # 返回成功响应
    return ok_no_store(response, data)