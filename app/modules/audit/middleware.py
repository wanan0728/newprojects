# 3.4 app/modules/audit/middleware.py
# 审计日志中间件模块
#
# 这个文件实现了FastAPI中间件，用于在请求结束时自动将审计事件写入数据库。
# 中间件会在请求处理完成后（无论成功还是失败）执行，确保审计日志被持久化。
# 如果请求过程中没有产生审计事件但有错误，也会自动创建一个错误审计记录。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入logging模块，用于记录日志
import logging

# 从fastapi导入Request类，用于获取请求信息
from fastapi import Request

# 从请求上下文模块导入各种上下文信息获取函数
from app.core.request_context import (
    get_client_ip,  # 获取客户端IP
    get_request_id,  # 获取请求ID
    get_user_agent,  # 获取User-Agent
    get_user_id,  # 获取用户ID
    get_workspace_id,  # 获取工作空间ID
)

# 从审计上下文模块导入审计上下文管理函数
from app.modules.audit.context import (
    clear_audit_context,  # 清除审计上下文
    init_audit_context,  # 初始化审计上下文
    pop_audit_events,  # 取出所有审计事件并清空
)

# 从审计模型模块导入AuditEvent模型，用于保存到数据库
from app.modules.audit.models import AuditEvent

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 定义init_audit函数，用于初始化审计上下文
# 这个函数会在请求开始时调用
def init_audit() -> None:
    # 调用init_audit_context初始化审计上下文（创建一个空列表）
    init_audit_context()


# 定义_classify函数，根据HTTP状态码分类操作状态
# status_code: int HTTP状态码
# -> str 返回分类结果："ok"（成功）、"deny"（拒绝）、"error"（错误）
def _classify(status_code: int) -> str:
    # 如果状态码是401（未授权）、403（禁止）、429（限流），属于"拒绝"类
    if status_code in {401, 403, 429}:
        return "deny"

    # 如果状态码大于等于400（其他客户端错误或服务器错误），属于"错误"类
    if status_code >= 400:
        return "error"

    # 其他情况（200-399），属于"成功"类
    return "ok"


# 定义flush_audit函数，用于在请求结束时将审计事件刷新到数据库
# request: Request FastAPI请求对象
# response: 响应对象（可以是Response或任何有status_code属性的对象）
async def flush_audit(request: Request, response) -> None:
    try:
        # 获取响应状态码，如果获取不到默认为500
        # getattr(response, "status_code", 500) 安全获取status_code属性
        # or 500 处理status_code为None的情况
        status_code = int(getattr(response, "status_code", 500) or 500)

        # 从审计上下文中取出所有审计事件（并清空上下文）
        events = pop_audit_events()

        # 如果没有审计事件，并且状态码大于等于400（有错误）
        if not events and status_code >= 400:
            # 获取请求ID、用户ID、工作空间ID
            rid = get_request_id()
            uid = get_user_id()
            wid = get_workspace_id()

            # 创建一个默认的错误审计事件
            events = [
                {
                    "request_id": rid,  # 请求ID
                    "workspace_id": wid,  # 工作空间ID
                    "actor_user_id": uid,  # 操作用户ID
                    "action": "http.error",  # 操作名称：HTTP错误
                    "scope_key": None,  # 作用域键：无
                    "resource_type": None,  # 资源类型：无
                    "resource_ref_id": None,  # 资源ID：无
                    "status": _classify(status_code),  # 状态：根据状态码分类
                    "http_status": status_code,  # HTTP状态码
                    "ip": str(get_client_ip()) if get_client_ip() else None,  # 客户端IP
                    "user_agent": str(get_user_agent()) if get_user_agent() else None,  # User-Agent
                    "meta": {  # 元数据：请求方法和路径
                        "method": request.method,
                        "path": request.url.path,
                    },
                }
            ]

        # 如果还是没有事件（可能没有错误且没有手动记录审计），直接返回
        if not events:
            return

        # 获取当前工作空间ID（可能已经变化）
        wid2 = get_workspace_id()

        # 从请求的app.state中获取数据库会话工厂
        session_maker = request.app.state.db_session_maker

        # 创建数据库会话
        async with session_maker() as db:
            # 开始事务（async with db.begin()会自动提交/回滚）
            async with db.begin():
                # 遍历所有审计事件
                for e in events:
                    # 如果事件中没有http_status，用响应的状态码填充
                    if e.get("http_status") is None:
                        e["http_status"] = status_code

                    # 如果事件中没有workspace_id，用当前工作空间ID填充
                    if e.get("workspace_id") is None:
                        e["workspace_id"] = wid2

                    # 将事件添加到数据库会话中
                    # **e 将字典解包为关键字参数，相当于 AuditEvent(request_id=e['request_id'], ...)
                    db.add(AuditEvent(**e))

    except Exception:
        # 如果发生异常，记录错误日志但不影响主流程
        # 审计失败不应该影响业务请求
        logger.exception("audit_flush_failed")

    finally:
        # 无论成功还是失败，最后都要清除审计上下文
        # 防止影响下一个请求
        clear_audit_context()