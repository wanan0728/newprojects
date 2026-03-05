# 4.4 app/api/openapi.py
# OpenAPI文档定制模块
#
# 这个文件用于定制FastAPI自动生成的OpenAPI文档（即Swagger UI）。
# 主要功能包括：统一添加响应头、添加错误响应模型、为特定接口添加缓存控制头。
# 这样可以让API文档更完整、更准确，方便前端和后端开发人员查看和使用。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi导入FastAPI应用类
from fastapi import FastAPI
# 从fastapi.openapi.utils导入get_openapi函数，用于生成OpenAPI schema
from fastapi.openapi.utils import get_openapi

# 从HTTP常量模块导入响应头字段名
from app.core.http_consts import HDR_CACHE_CONTROL, HDR_REQUEST_ID, HDR_RESPONSE_TIME_MS
# 从路由常量模块导入不应被缓存的路径集合
from app.api.routes_consts import NO_STORE_PATHS

# 定义通用响应头字典，所有接口都会添加这些响应头
_COMMON_RESPONSE_HEADERS = {
    # 请求ID头：用于追踪请求链路
    HDR_REQUEST_ID: {
        "description": "Request correlation id",  # 描述：请求关联ID
        "schema": {"type": "string"},  # 类型：字符串
    },
    # 响应耗时头：服务器处理时间
    HDR_RESPONSE_TIME_MS: {
        "description": "Server processing time in milliseconds",  # 描述：服务器处理时间（毫秒）
        "schema": {"type": "string"},  # 类型：字符串
    },
}

# 定义禁止缓存的响应头，用于敏感接口
_NO_STORE_HEADER = {
    HDR_CACHE_CONTROL: {
        "description": "Sensitive response, do not store",  # 描述：敏感响应，不要缓存
        "schema": {"type": "string", "example": "no-store"},  # 类型：字符串，示例值：no-store
    }
}


# 定义_merge_responses函数，合并响应字典
# dest: dict 目标字典
# src: dict 源字典
def _merge_responses(dest: dict, src: dict) -> None:
    """
    将源字典中的响应定义合并到目标字典中

    如果目标字典中不存在某个键，则添加。
    """
    # 遍历源字典的每个键值对
    for k, v in src.items():
        # 如果目标字典中没有这个键，就添加
        if k not in dest:
            dest[k] = v


# 定义_ensure_error_response_schema函数，确保OpenAPI schema中包含错误响应模型
# schema: dict OpenAPI schema字典
def _ensure_error_response_schema(schema: dict) -> None:
    """
    确保OpenAPI schema中定义了ErrorResponse和ErrorInfo模型

    这样在文档中就可以统一引用这些错误响应模型。
    """
    # 获取或创建components部分
    comps = schema.setdefault("components", {})
    # 获取或创建schemas部分
    schemas = comps.setdefault("schemas", {})

    # 如果还没有定义ErrorResponse
    if "ErrorResponse" not in schemas:
        # 先定义ErrorInfo模型
        schemas["ErrorInfo"] = {
            "title": "ErrorInfo",  # 标题
            "type": "object",  # 类型：对象
            "properties": {  # 属性定义
                "code": {"type": "string"},  # 错误码：字符串
                "message": {},  # 错误消息：任意类型
                "request_id": {"type": "string"},  # 请求ID：字符串
                "meta": {"type": "object", "additionalProperties": True},  # 元数据：任意对象
            },
            "required": ["code", "message", "request_id"],  # 必填字段
        }
        # 再定义ErrorResponse模型（包装ErrorInfo）
        schemas["ErrorResponse"] = {
            "title": "ErrorResponse",  # 标题
            "type": "object",  # 类型：对象
            "properties": {  # 属性定义
                "error": {"$ref": "#/components/schemas/ErrorInfo"}  # 引用ErrorInfo
            },
            "required": ["error"],  # 必填字段
        }


# 定义_err_resp函数，创建错误响应的描述字典
# desc: str 错误描述
# -> dict 返回错误响应定义
def _err_resp(desc: str) -> dict:
    """
    创建一个标准错误响应的定义

    参数:
        desc: 错误描述，如"Unauthorized"

    返回:
        错误响应定义字典，引用ErrorResponse模型
    """
    return {
        "description": desc,  # 响应描述
        "content": {  # 响应内容
            "application/json": {  # JSON格式
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}  # 引用ErrorResponse模型
            }
        },
    }


# 定义install_openapi函数，安装自定义OpenAPI生成器
# app: FastAPI FastAPI应用实例
def install_openapi(app: FastAPI) -> None:
    """
    安装自定义OpenAPI生成器

    替换app.openapi方法，在生成文档时添加：
    1. 错误响应模型
    2. 通用响应头
    3. 对敏感接口添加Cache-Control: no-store头
    """

    # 定义内部函数custom_openapi，用于生成自定义的OpenAPI schema
    def custom_openapi():
        # 如果已经生成过schema，直接返回缓存的结果
        if app.openapi_schema:
            return app.openapi_schema

        # 调用FastAPI的get_openapi生成基础schema
        schema = get_openapi(
            title=app.title,  # API标题
            version=getattr(app, "version", "0.1.0"),  # API版本
            description=app.description,  # API描述
            routes=app.routes,  # 所有路由
        )

        # 确保schema中包含错误响应模型
        _ensure_error_response_schema(schema)

        # 定义通用的错误响应列表
        common_error_responses: dict[str, dict] = {
            "400": _err_resp("Bad Request"),  # 400: 错误请求
            "401": _err_resp("Unauthorized"),  # 401: 未授权
            "403": _err_resp("Forbidden"),  # 403: 禁止访问
            "404": _err_resp("Not Found"),  # 404: 未找到
            "409": _err_resp("Conflict"),  # 409: 冲突
            "422": _err_resp("Validation Failed"),  # 422: 验证失败
            "429": _err_resp("Rate Limited"),  # 429: 限流
            "500": _err_resp("Internal Error"),  # 500: 内部错误
        }

        # 获取paths部分（所有接口路径）
        paths = schema.get("paths", {})
        # 如果paths是字典，遍历每个路径
        if isinstance(paths, dict):
            for path, path_item in paths.items():
                # path_item可能是None或不是字典，跳过
                if not isinstance(path_item, dict):
                    continue

                # 遍历路径下的每个HTTP方法（get、post等）
                for _, op in path_item.items():
                    # op可能是None或不是字典，跳过
                    if not isinstance(op, dict):
                        continue

                    # 获取该操作的responses定义
                    responses = op.get("responses")
                    # 如果没有responses，创建一个空字典
                    if not isinstance(responses, dict):
                        responses = {}
                        op["responses"] = responses

                    # 合并通用错误响应
                    _merge_responses(responses, common_error_responses)

                    # 判断当前路径是否属于"不缓存"的路径集合
                    is_no_store_endpoint = path in NO_STORE_PATHS

                    # 遍历每个响应状态码
                    for _, resp in responses.items():
                        # resp可能是None或不是字典，跳过
                        if not isinstance(resp, dict):
                            continue

                        # 获取或创建headers定义
                        hdrs = resp.get("headers")
                        if not isinstance(hdrs, dict):
                            hdrs = {}
                            resp["headers"] = hdrs

                        # 添加通用响应头（请求ID、响应时间）
                        for hk, hv in _COMMON_RESPONSE_HEADERS.items():
                            # 如果这个头还没定义，才添加（避免覆盖）
                            hdrs.setdefault(hk, hv)

                        # 如果是敏感接口，添加禁止缓存头
                        if is_no_store_endpoint:
                            for hk, hv in _NO_STORE_HEADER.items():
                                hdrs.setdefault(hk, hv)

        # 缓存生成的schema
        app.openapi_schema = schema
        return app.openapi_schema

    # 替换app.openapi方法
    app.openapi = custom_openapi