# 3.3 app/modules/audit/service.py
# 审计日志服务模块
#
# 这个文件提供了记录审计日志的核心函数。
# 程序中到处都会看到这个函数的调用，只要调用这个函数就是在做审计。
# 它会自动收集请求上下文信息（请求ID、用户ID、IP等），
# 并格式化成标准格式后添加到审计上下文中。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入dataclasses模块，用于处理数据类对象
import dataclasses

# 从typing导入Any，表示任意类型
from typing import Any

# 从pydantic导入BaseModel，用于判断和处理Pydantic模型
from pydantic import BaseModel

# 从脱敏模块导入redact_obj，用于对敏感信息进行脱敏
from app.core.redaction import redact_obj

# 从请求上下文模块导入各种上下文信息获取函数
from app.core.request_context import (
    get_client_ip,  # 获取客户端IP
    get_request_id,  # 获取请求ID
    get_user_agent,  # 获取User-Agent
    get_user_id,  # 获取用户ID
    get_workspace_id,  # 获取工作空间ID
)

# 从审计上下文模块导入添加审计事件的函数
from app.modules.audit.context import add_audit_event


# 定义_to_obj函数，将任意对象转换为可JSON序列化的基本类型
# v: Any 输入任意类型的对象
# -> Any 返回转换后的基本类型
def _to_obj(v: Any) -> Any:
    # 如果值是None，直接返回None
    if v is None:
        return None

    # 如果值是基本类型（字符串、整数、浮点数、布尔值），直接返回
    if isinstance(v, (str, int, float, bool)):
        return v

    # 如果值是Pydantic模型，调用model_dump()转换为字典
    if isinstance(v, BaseModel):
        return v.model_dump()

    # 如果值是数据类（@dataclass），调用asdict()转换为字典
    if dataclasses.is_dataclass(v):
        return dataclasses.asdict(v)

    # 如果值是字典，递归处理每个键值对
    if isinstance(v, dict):
        # 将键转换为字符串，值递归处理
        return {str(k): _to_obj(x) for k, x in v.items()}

    # 如果值是列表、元组或集合，递归处理每个元素
    if isinstance(v, (list, tuple, set)):
        # 返回处理后的列表
        return [_to_obj(x) for x in v]

    # 其他类型（如自定义类），转换为字符串
    return str(v)


# 定义_normalize_meta函数，规范化元数据格式
# meta: Any | None 输入的元数据，可以是任意类型
# -> dict[str, Any] | None 返回规范化后的字典或None
def _normalize_meta(meta: Any | None) -> dict[str, Any] | None:
    # 如果meta是None，返回None
    if meta is None:
        return None

    # 如果meta是字典，处理每个键值对
    if isinstance(meta, dict):
        # 键转字符串，值递归处理
        return {str(k): _to_obj(v) for k, v in meta.items()}

    # 如果meta不是字典（如单个值），包装成{"value": 处理后的值}
    return {"value": _to_obj(meta)}


# 定义_std_meta函数，生成标准化的元数据（带脱敏和错误码）
# meta: Any | None 输入的元数据
# error_code: str | None 错误码（如果有）
# -> dict[str, Any] | None 返回处理后的元数据
def _std_meta(*, meta: Any | None, error_code: str | None) -> dict[str, Any] | None:
    # 先规范化元数据
    m = _normalize_meta(meta)

    # 如果没有错误码，直接返回脱敏后的元数据
    if error_code is None:
        return redact_obj(m)

    # 如果有错误码
    if m is None:
        # 如果元数据是None，创建一个只包含错误码的字典
        m2: dict[str, Any] = {"error_code": str(error_code)}
    else:
        # 如果元数据存在，复制一份
        m2 = dict(m)
        # 添加错误码（如果不存在）
        m2.setdefault("error_code", str(error_code))

    # 返回脱敏后的元数据
    return redact_obj(m2)


# 定义record函数，记录审计事件
# 这个函数只是做审计，程序中到处都会看到这个函数的调用。
# 只要调用这个函数就是在做审计。
#
# 参数说明（全部是关键字参数，必须写参数名）：
#   action: 操作名称，如 "create_user", "delete_document"
#   status: 操作状态，默认"ok"，可选"deny"、"error"
#   http_status: HTTP状态码，如200、403、500
#   scope_key: 作用域键，用于区分不同功能模块
#   resource_type: 资源类型，如 "user", "document"
#   resource_ref_id: 资源ID，如用户ID、文档ID
#   actor_user_id: 操作用户ID（如果不传，会自动从上下文获取）
#   meta: 额外的元数据，可以是任意类型
#   error_code: 错误码（如果有）
# -> None 无返回值
def record(
        *,
        action: str,
        status: str = "ok",
        http_status: int | None = None,
        scope_key: str | None = None,
        resource_type: str | None = None,
        resource_ref_id: int | None = None,
        actor_user_id: int | None = None,
        meta: Any | None = None,
        error_code: str | None = None,
) -> None:
    # 构建审计事件字典
    evt = {
        # 请求ID：从上下文获取
        "request_id": get_request_id(),

        # 工作空间ID：从上下文获取
        "workspace_id": get_workspace_id(),

        # 操作用户ID：如果传了就用传的，否则从上下文获取
        "actor_user_id": actor_user_id if actor_user_id is not None else get_user_id(),

        # 操作名称：转成字符串
        "action": str(action),

        # 作用域键：如果有就转成字符串
        "scope_key": str(scope_key) if scope_key is not None else None,

        # 资源类型：如果有就转成字符串
        "resource_type": str(resource_type) if resource_type is not None else None,

        # 资源ID：如果有就转成整数
        "resource_ref_id": int(resource_ref_id) if resource_ref_id is not None else None,

        # 状态：转成字符串
        "status": str(status),

        # HTTP状态码：如果有就转成整数
        "http_status": int(http_status) if http_status is not None else None,

        # 客户端IP：从上下文获取
        "ip": str(get_client_ip()) if get_client_ip() else None,

        # User-Agent：从上下文获取
        "user_agent": str(get_user_agent()) if get_user_agent() else None,

        # 元数据：调用_std_meta处理（规范化 + 脱敏 + 错误码）
        "meta": _std_meta(meta=meta, error_code=error_code),
    }

    # 将审计事件添加到审计上下文中
    # 后续会在请求结束时统一保存到数据库
    add_audit_event(evt)