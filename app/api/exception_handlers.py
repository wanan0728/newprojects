# 4.3 app/api/exception_handlers.py
# 全局异常处理器模块
#
# handlers通常表示处理器，这个文件定义了FastAPI应用的全局异常处理器。
# 它的作用是统一处理所有类型的异常，确保即使发生错误，返回给客户端的响应格式也是统一的，
# 同时自动记录审计日志，方便问题排查。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入logging模块，用于记录日志
import logging
# 导入uuid模块，用于生成唯一的请求ID
import uuid
# 从typing导入Any，表示任意类型
from typing import Any

# 从fastapi导入Request和异常类
from fastapi import Request
# RequestValidationError: 请求数据验证失败时抛出的异常
from fastapi.exceptions import RequestValidationError
# JSONResponse: 返回JSON格式的响应
from fastapi.responses import JSONResponse
# StarletteHTTPException: Starlette框架的HTTP异常基类
from starlette.exceptions import HTTPException as StarletteHTTPException

# 从API模式模块导入错误响应模型
from app.core.api_schemas import ErrorInfo, ErrorResponse
# 从错误处理模块导入自定义异常和错误消息解析函数
from app.core.errors import AppError, resolve_message
# 从HTTP常量模块导入请求ID相关的常量
from app.core.http_consts import HDR_REQUEST_ID, STATE_REQUEST_ID
# 从审计钩子模块导入记录审计事件的函数
from app.modules.audit.hook import record

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


# 定义_get_request_id函数，用于从请求中获取请求ID
# request: Request 参数，FastAPI请求对象
# -> str 返回请求ID字符串
def _get_request_id(request: Request) -> str:
    # 尝试从请求状态中获取请求ID
    # getattr(request.state, STATE_REQUEST_ID, None) 安全获取属性，不存在返回None
    rid = getattr(request.state, STATE_REQUEST_ID, None)

    # 如果获取到的是字符串且不为空，直接返回
    if isinstance(rid, str) and rid:
        return rid

    # 如果状态中没有，尝试从请求头中获取
    # 客户端可能通过X-Request-Id头传递了请求ID
    rid = request.headers.get(HDR_REQUEST_ID)
    if rid:
        return rid

    # 以上两个if就是通过各种渠道检查一个请求有没有带rid（request id），
    # 如果有就返回，没有下一步创建

    # 如果都没有，生成一个新的UUID作为请求ID
    return uuid.uuid4().hex


# 定义_build_error函数，创建标准化的错误响应字典
# code: str 错误码
# message: Any 错误消息
# request_id: str 请求ID
# meta: dict[str, Any] | None = None 额外的元数据
# -> dict 返回格式化的错误响应字典
def _build_error(
        *,
        code: str,
        message: Any,
        request_id: str,
        meta: dict[str, Any] | None = None,
) -> dict:
    # 创建一个ErrorResponse对象，包装错误信息
    # ErrorResponse(error=ErrorInfo(...)) 符合API规范
    payload = ErrorResponse(
        error=ErrorInfo(
            code=code,  # 错误码
            message=message,  # 错误消息
            request_id=request_id,  # 请求ID
            meta=meta  # 额外元数据
        )
    )
    # 调用model_dump()将Pydantic模型转换为字典
    # 将结果变成字典，方便JSON序列化
    return payload.model_dump()


# 定义install_exception_handlers函数，安装异常处理器到FastAPI应用
# app 参数，FastAPI应用实例
def install_exception_handlers(app) -> None:
    # 这个方法稍后用于安装异常处理器，我们下面有4个异常处理器

    # 使用装饰器注册AppError异常处理器
    # 每一个异常处理器都要说明它是用于来处理哪种异常的
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """处理自定义的AppError异常"""
        # 获取请求ID
        rid = _get_request_id(request)
        # 获取HTTP状态码
        st = int(exc.http_status)

        # 记录审计日志
        record(
            action="http.app_error",  # 操作名称：应用错误
            status="error" if st >= 500 else "deny" if st in {401, 403, 429} else "error",  # 状态分类
            http_status=st,  # HTTP状态码
            meta={"path": request.url.path, "method": request.method},  # 请求信息
            error_code=str(exc.code),  # 错误码
        )

        # 返回JSON格式的错误响应
        return JSONResponse(
            status_code=st,  # HTTP状态码
            content=_build_error(  # 错误内容
                code=str(exc.code),
                message=exc.message,
                request_id=rid,
                meta=exc.meta,
            ),
            headers={HDR_REQUEST_ID: rid},  # 响应头中加入请求ID
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """处理请求数据验证失败异常"""
        # 获取请求ID
        rid = _get_request_id(request)

        # 记录审计日志
        record(
            action="http.validation_failed",  # 操作名称：验证失败
            status="deny",  # 状态：拒绝
            http_status=422,  # HTTP状态码：422 Unprocessable Entity
            meta={  # 元数据：包含详细的验证错误信息
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),  # 验证错误详情
            },
            error_code="error.validation_failed",  # 错误码
        )

        # 返回422错误响应
        return JSONResponse(
            status_code=422,
            content=_build_error(
                code="error.validation_failed",
                message=resolve_message("error.validation_failed"),  # 获取错误消息
                request_id=rid,
                meta={"errors": exc.errors()},  # 将验证错误详情放入meta
            ),
            headers={HDR_REQUEST_ID: rid},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理HTTP异常（如404、405等）"""
        # 获取请求ID
        rid = _get_request_id(request)
        # 获取异常详情
        detail = exc.detail

        # 初始化错误码和消息
        code = "error.http"
        msg = resolve_message(code, "http_error")
        meta: dict[str, Any] | None = None

        # 解析异常详情中的错误信息
        # 如果detail是字典，可能包含了自定义的错误码和消息
        if isinstance(detail, dict) and "code" in detail:
            # 从字典中提取错误码
            code = str(detail.get("code"))
            # 提取错误消息，如果没有则用错误码
            msg = detail.get("message", resolve_message(code, code))
            # 提取元数据
            meta_val = detail.get("meta")
            if meta_val is None:
                meta = None
            elif isinstance(meta_val, dict):
                meta = meta_val
            else:
                meta = {"value": meta_val}
        # 如果detail是字符串，直接作为错误码
        elif isinstance(detail, str) and detail.strip():
            code = detail.strip()
            msg = resolve_message(code, code)
            meta = None

        # 记录审计日志
        record(
            action="http.http_exception",
            status="deny" if int(exc.status_code) in {401, 403, 429} else "error",
            http_status=int(exc.status_code),
            meta={"path": request.url.path, "method": request.method, "detail_meta": meta},
            error_code=str(code),
        )

        # 返回HTTP异常响应
        return JSONResponse(
            status_code=int(exc.status_code),
            content=_build_error(code=code, message=msg, request_id=rid, meta=meta),
            headers={HDR_REQUEST_ID: rid},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常（最后的防线）"""
        # 获取请求ID
        rid = _get_request_id(request)

        # 记录错误日志，包含完整的异常堆栈
        logger.error(
            "unhandled_error",
            extra={"request_id": rid},
            exc_info=(type(exc), exc, exc.__traceback__),  # 包含异常堆栈信息
        )

        # 记录审计日志
        record(
            action="http.unhandled_error",  # 操作名称：未处理的错误
            status="error",  # 状态：错误
            http_status=500,  # HTTP状态码：500
            meta={  # 元数据：异常信息
                "path": request.url.path,
                "method": request.method,
                "exc_type": exc.__class__.__name__,  # 异常类型名
            },
            error_code="error.internal",  # 错误码：内部错误
        )

        # 返回500错误响应
        return JSONResponse(
            status_code=500,
            content=_build_error(
                code="error.internal",
                message=resolve_message("error.internal"),  # "internal_error"
                request_id=rid,
            ),
            headers={HDR_REQUEST_ID: rid},
        )