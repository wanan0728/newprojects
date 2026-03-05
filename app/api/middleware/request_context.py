# 4.8 app/api/middleware/request_context.py
# 请求上下文中间件模块
#
# 这个中间件负责在每个请求开始时初始化请求上下文，并在请求结束时清理。
# 主要功能包括：处理请求ID、设置上下文变量（用户ID、IP等）、记录响应时间、
# 触发审计日志等。它是整个应用请求处理流程的核心组件。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入inspect模块，用于检查对象是否为协程等
import inspect
# 导入re模块，用于正则表达式验证请求ID格式
import re
# 导入time模块，用于计算请求处理时间
import time
# 导入uuid模块，用于生成唯一的请求ID
import uuid

# 从fastapi导入Request类
from fastapi import Request
# 从starlette.background导入BackgroundTask，用于在响应后执行后台任务
from starlette.background import BackgroundTask
# 从starlette.middleware.base导入BaseHTTPMiddleware，用于创建中间件
from starlette.middleware.base import BaseHTTPMiddleware

# 从real_ip模块导入获取真实IP的函数
from app.api.middleware.real_ip import get_real_ip
# 从HTTP常量模块导入请求ID和响应时间的头字段名
from app.core.http_consts import HDR_REQUEST_ID, HDR_RESPONSE_TIME_MS, STATE_REQUEST_ID
# 从请求上下文模块导入设置上下文变量的函数
from app.core.request_context import (
    set_client_ip,  # 设置客户端IP
    set_request_id,  # 设置请求ID
    set_user_agent,  # 设置User-Agent
    set_user_id,  # 设置用户ID
    set_workspace_id  # 设置工作空间ID
)
# 从审计钩子模块导入初始化和刷新审计的函数
from app.modules.audit.hook import flush_audit, init_audit

# 定义请求ID的最大长度
_MAX_RID_LEN = 128
# 定义安全的请求ID正则表达式：只允许字母、数字、点、下划线、短横线，长度1-128
_RE_SAFE_RID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


# 定义_sanitize_request_id函数，清理和验证请求ID
# v: str | None 输入的请求ID
# -> str 返回安全的请求ID
def _sanitize_request_id(v: str | None) -> str:
    """
    清理和验证请求ID，如果不合法则生成新的UUID

    规则：
    1. 如果v为空，生成新UUID
    2. 如果v太长（超过128），生成新UUID
    3. 如果v包含非法字符，生成新UUID
    4. 否则返回原字符串
    """
    # 如果v为空，直接生成新的UUID
    if not v:
        return uuid.uuid4().hex

    # 去掉首尾空格
    v = v.strip()

    # 如果去掉空格后为空，或者长度超过最大限制，生成新UUID
    if not v or len(v) > _MAX_RID_LEN:
        return uuid.uuid4().hex

    # 如果不符合正则表达式（包含非法字符），生成新UUID
    if not _RE_SAFE_RID.match(v):
        return uuid.uuid4().hex

    # 验证通过，返回原字符串
    return v


# 定义_finalize_request函数，在请求结束时执行清理工作
# request: Request 请求对象
# response: 响应对象
async def _finalize_request(request: Request, response) -> None:
    """
    请求结束时的清理任务

    1. 刷新审计日志
    2. 清空上下文变量
    """
    try:
        # 刷新审计日志（将审计事件写入数据库）
        await flush_audit(request, response)
    finally:
        # 无论审计是否成功，都要清空上下文变量
        # 防止影响下一个请求
        set_request_id(None)  # 清空请求ID
        set_user_id(None)  # 清空用户ID
        set_workspace_id(None)  # 清空工作空间ID
        set_client_ip(None)  # 清空客户端IP
        set_user_agent(None)  # 清空User-Agent


# 定义RequestContextMiddleware类，继承自BaseHTTPMiddleware
# 这是FastAPI/Starlette的中间件基类
class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件

    在请求处理前：
    - 处理请求ID
    - 设置上下文变量（请求ID、用户ID、IP等）
    - 初始化审计上下文

    在请求处理后：
    - 计算响应时间
    - 添加响应头（请求ID、响应时间）
    - 注册后台任务（刷新审计、清理上下文）
    """

    # 重写dispatch方法，这是中间件的核心方法
    # request: Request 请求对象
    # call_next: 调用下一个中间件或路由处理函数
    async def dispatch(self, request: Request, call_next):
        """
        处理每个请求
        """
        # === 请求前处理 ===

        # 从请求头获取请求ID，并进行清理验证
        rid = _sanitize_request_id(request.headers.get(HDR_REQUEST_ID))

        # 将请求ID存入request.state，方便后续获取
        setattr(request.state, STATE_REQUEST_ID, rid)

        # 将请求ID设置到上下文变量中
        set_request_id(rid)
        # 初始化用户ID为None（后续由认证中间件设置）
        set_user_id(None)

        # 获取工作空间ID（可能由其他中间件设置）
        wid = getattr(request.state, "workspace_id", None)
        # 设置到上下文变量
        set_workspace_id(wid)

        # 获取真实客户端IP，设置到上下文
        set_client_ip(get_real_ip(request))
        # 获取User-Agent，设置到上下文
        set_user_agent(request.headers.get("User-Agent"))

        # 初始化审计上下文（创建一个空列表）
        init_audit()

        # 记录开始时间（高精度计时器）
        start = time.perf_counter()

        # === 调用下一个中间件或路由处理函数 ===
        resp = await call_next(request)

        # === 请求后处理 ===

        # 计算处理耗时（毫秒）
        cost_ms = int((time.perf_counter() - start) * 1000)

        # 添加响应头
        resp.headers[HDR_REQUEST_ID] = rid  # 返回请求ID，方便客户端追踪
        resp.headers[HDR_RESPONSE_TIME_MS] = str(cost_ms)  # 返回处理耗时

        # 注册后台任务（在响应发送后执行）
        if resp.background is None:
            # 如果没有后台任务，直接设置我们的清理任务
            resp.background = BackgroundTask(_finalize_request, request, resp)
        else:
            # 如果已经有后台任务，需要链式执行
            prev = resp.background

            # 定义链式执行函数
            async def _chain() -> None:
                # 先执行原有的后台任务
                r = prev()
                # 如果原有任务是协程，等待它完成
                if inspect.isawaitable(r):
                    await r
                # 再执行我们的清理任务
                await _finalize_request(request, resp)

            # 将后台任务替换为链式任务
            resp.background = BackgroundTask(_chain)

        # 返回响应
        return resp