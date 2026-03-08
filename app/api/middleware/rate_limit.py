# 4.12 app/api/middleware/rate_limit.py
# 限流中间件模块
#
# 这个文件提供了基于Redis的限流功能，用于限制客户端在指定时间窗口内的请求次数。
# 限流可以防止恶意攻击、保护后端服务不被过度请求，确保服务的稳定性。
# 支持按IP、用户、工作空间等多种维度进行限流。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入time模块，用于获取当前时间戳
import time
# 从dataclasses导入dataclass装饰器，用于定义数据类
from dataclasses import dataclass
# 从typing导入Callable，用于类型提示
from typing import Callable

# 从fastapi导入Depends和Request
# Depends: 用于创建依赖项
# Request: FastAPI请求对象
from fastapi import Depends, Request
# 从redis.exceptions导入RedisError，用于捕获Redis异常
from redis.exceptions import RedisError

# 从real_ip模块导入获取真实IP的函数
from app.api.middleware.real_ip import get_real_ip
# 从错误处理模块导入抛出异常的函数
from app.core.errors import raise_err
# 从请求上下文模块导入获取工作空间ID的函数
from app.core.request_context import get_workspace_id
# 从Redis客户端模块导入获取Redis连接的依赖
from app.infra.redis_client import get_redis
# 从审计钩子模块导入记录审计事件的函数
from app.modules.audit.hook import record

# 定义Redis键的前缀，用于区分不同类型的键
RL_REDIS_KEY_PREFIX = "rl"


# 定义RateLimitSpec数据类，用于描述限流规则
# frozen=True 表示这个类的实例是不可变的（只读）
@dataclass(frozen=True)
class RateLimitSpec:
    name: str  # 限流规则名称，如 "auth_login", "api_request"
    limit: int  # 限制次数，如 10
    window_seconds: int  # 时间窗口（秒），如 60


# 定义_to_int函数，将传入的对象转换为整数
# v: object 传入的对象
# -> int | None 返回整数或None
def _to_int(v: object) -> int | None:
    """
    将传入的参数转换为整数

    支持的类型：
    - None: 返回None
    - 字符串: 尝试转换为整数
    - 字节串: 先解码为UTF-8，再转换
    - 其他: 直接转换
    转换失败返回None
    """
    # 如果v是None，直接返回None
    if v is None:
        return None

    # 如果v是字节类型（bytes、bytearray）
    if isinstance(v, (bytes, bytearray)):
        try:
            # 尝试用UTF-8解码为字符串
            v = v.decode("utf-8")
        except UnicodeDecodeError:
            # 解码失败返回None
            return None

    # 尝试将v转换为整数
    try:
        return int(v)
    except (TypeError, ValueError):
        # 转换失败返回None
        return None


# 定义_norm_identifier函数，规范化标识符字符串
# s: str 输入的标识符
# -> str 返回规范化后的字符串
def _norm_identifier(s: str) -> str:
    """
    规范化标识符，用于构建Redis键

    例如：
    - 空字符串 -> "unknown"
    - "192.168.1.1" -> "192.168.1.1"
    - "user@example.com" -> "user_example.com" (空格和|被替换)
    """
    # 去掉首尾空格，如果为空则返回"unknown"
    s = (s or "").strip()
    if not s:
        return "unknown"
    # 将空格和竖线替换为下划线（避免Redis键格式问题）
    return s.replace(" ", "_").replace("|", "_")


# 定义_workspace_id_from_request函数，从请求中获取工作空间ID
# request: Request 请求对象
# -> int 返回工作空间ID，如果没有则返回0
def _workspace_id_from_request(request: Request) -> int:
    """
    从请求状态或上下文中获取工作空间ID

    优先级：
    1. request.state.workspace_id
    2. 上下文中的workspace_id

    如果都没有，返回0（表示无租户）
    """
    # 先从请求状态中获取
    wid = getattr(request.state, "workspace_id", None)

    # 如果请求状态中没有，从上下文中获取
    if wid is None:
        wid = get_workspace_id()

    # 尝试转换为整数
    try:
        wid_i = int(wid) if wid is not None else 0
    except Exception:
        # 转换失败返回0
        wid_i = 0

    # 返回正数ID，否则返回0
    return wid_i if wid_i > 0 else 0


# 定义_key_fixed_window函数，构建固定时间窗口限流的Redis键
# name: str 限流规则名称
# workspace_id: int 工作空间ID
# identifier: str 标识符（如IP、用户ID）
# window_seconds: int 时间窗口（秒）
# now_ts: int 当前时间戳
# -> str 返回Redis键
def _key_fixed_window(name: str, workspace_id: int, identifier: str, window_seconds: int, now_ts: int) -> str:
    """
    构建固定时间窗口的Redis键

    格式：rl:{name}:ws:{workspace_id}:{identifier}:{bucket}
    bucket = now_ts // window_seconds  # 当前时间属于第几个时间窗口

    例如：rl:auth_login:ws:1:192.168.1.1:2870
    """
    # 计算当前时间属于哪个时间窗口
    bucket = now_ts // int(window_seconds)
    # 返回格式化的键名
    return f"{RL_REDIS_KEY_PREFIX}:{name}:ws:{int(workspace_id)}:{identifier}:{bucket}"


# 定义rate_limit_ip函数，创建基于IP的限流依赖项
# spec: RateLimitSpec 限流规则
# -> Callable 返回一个FastAPI依赖项函数
def rate_limit_ip(spec: RateLimitSpec) -> Callable:
    """
    创建基于IP地址的限流依赖项

    用法示例：
    rate_limit = rate_limit_ip(RateLimitSpec(name="auth_login", limit=10, window_seconds=60))

    @app.post("/login")
    async def login(_: None = Depends(rate_limit)):
        # 这个接口每分钟每个IP最多只能请求10次
        ...
    """

    # 定义内部异步函数_dep，作为FastAPI依赖项
    async def _dep(request: Request, redis=Depends(get_redis)):
        # 获取客户端真实IP，并规范化
        ip = _norm_identifier(get_real_ip(request) or "unknown")

        # 获取工作空间ID
        wid = _workspace_id_from_request(request)

        # 获取当前时间戳
        now = int(time.time())

        # 构建Redis键
        k = _key_fixed_window(
            spec.name,  # 规则名称
            wid,  # 工作空间ID
            ip,  # IP地址
            int(spec.window_seconds),  # 时间窗口
            now  # 当前时间戳
        )

        # === 第1步：增加计数器 ===
        try:
            # redis.incr(k) 将键的值增加1，返回增加后的值
            n_raw = await redis.incr(k)
        except RedisError:
            # Redis操作失败，抛出内部错误
            raise_err(
                "error.internal",
                meta={"where": "rate_limit", "reason": "redis_incr_failed"}
            )

        # === 第2步：将结果转换为整数 ===
        n = _to_int(n_raw)
        if n is None:
            # 转换失败，抛出内部错误
            raise_err(
                "error.internal",
                meta={"where": "rate_limit", "reason": "bad_redis_incr"}
            )

        # === 第3步：如果是第一次请求，设置过期时间 ===
        if n == 1:
            # 获取过期时间（等于时间窗口长度）
            ttl = int(spec.window_seconds)
            if ttl <= 0:
                # 时间窗口无效，抛出内部错误
                raise_err(
                    "error.internal",
                    meta={"where": "rate_limit", "reason": "bad_window_seconds"}
                )

            try:
                # 设置键的过期时间（秒）
                await redis.expire(k, ttl)
            except RedisError:
                # 设置过期时间失败，尝试删除键
                try:
                    await redis.delete(k)
                except RedisError:
                    # 删除也失败，抛出内部错误
                    raise_err(
                        "error.internal",
                        meta={"where": "rate_limit", "reason": "redis_expire_failed"}
                    )

        # === 第4步：检查是否超过限制 ===
        if n > int(spec.limit):
            # 超过限制，记录审计日志
            record(
                action="http.rate_limited",  # 操作名称：被限流
                status="deny",  # 状态：拒绝
                http_status=429,  # HTTP状态码：429 Too Many Requests
                meta={
                    "name": str(spec.name),  # 规则名称
                    "limit": int(spec.limit),  # 限制次数
                    "window_seconds": int(spec.window_seconds),  # 时间窗口
                    "ip": ip,  # 客户端IP
                    "workspace_id": int(wid),  # 工作空间ID
                },
                error_code="error.rate_limited",  # 错误码
            )

            # 抛出限流异常
            raise_err(
                "error.rate_limited",
                meta={
                    "name": str(spec.name),
                    "limit": int(spec.limit),
                    "window_seconds": int(spec.window_seconds),
                    "workspace_id": int(wid),
                },
            )

        # 没有超过限制，继续处理请求
        # 注意：这里没有返回值，因为这是一个依赖项，不需要返回值

    # 返回内部函数
    return _dep