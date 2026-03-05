# 4.2 app/api/response.py
# API响应增强工具模块
#
# 这个文件在core/api_response.py的基础上，增加了与HTTP响应头相关的功能。
# 主要提供了设置缓存控制头的辅助函数，方便在返回数据时指定缓存策略。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从typing模块导入Any，表示任意类型
from typing import Any

# 从fastapi导入Response类
# Response是FastAPI的响应对象，用于设置响应头、状态码等
from fastapi import Response

# 从HTTP常量模块导入缓存控制头的字段名
# HDR_CACHE_CONTROL = "Cache-Control"
from app.core.http_consts import HDR_CACHE_CONTROL


# 定义no_store函数，用于设置响应头的缓存控制为"no-store"
# response: Response 参数，FastAPI的响应对象
# -> None 这个函数没有返回值
def no_store(response: Response) -> None:
    """
    设置响应头的缓存控制为"no-store"，告诉浏览器不要缓存这个响应

    参数:
        response: FastAPI响应对象
    """
    # 设置响应头的Cache-Control字段为"no-store"
    # "no-store" 表示浏览器绝对不能缓存这个响应，每次都必须重新请求
    # 适用于包含敏感信息或实时数据的接口
    response.headers[HDR_CACHE_CONTROL] = "no-store"
    # 返回的内容不缓存


# 定义ok_no_store函数，返回成功响应的同时设置不缓存
# response: Response 参数，FastAPI的响应对象
# data: Any 参数，要返回的数据
# meta: Any | None 参数，可选的元数据，默认为None
# -> dict 返回一个字典，格式为 {"data": data, "meta": meta}
def ok_no_store(response: Response, data: Any, *, meta: Any | None = None) -> dict:
    """
    返回成功响应，并设置响应头禁止缓存

    这个函数结合了两个功能：
    1. 使用core/api_response.py的ok函数格式化响应数据
    2. 设置Cache-Control: no-store头禁止缓存

    参数:
        response: FastAPI响应对象，用于设置响应头
        data: 要返回的数据
        meta: 可选的元数据

    返回:
        格式化后的响应字典
    """
    # 在函数内部导入ok函数，避免循环导入
    # 因为app.core.api_response可能也会导入这个模块
    from app.core.api_response import ok

    # 先调用no_store函数设置响应头，禁止缓存
    no_store(response)

    # 再调用ok函数格式化响应数据
    # 返回 {"data": data, "meta": meta} 格式的字典
    return ok(data, meta=meta)
    # 返回了一组数据，但是所有内容不要缓存

# 使用示例（在路径操作函数中）：
# from app.api.response import ok_no_store
# from fastapi import Response
#
# @app.get("/auth/me")
# async def get_current_user(response: Response):
#     user = {"id": 1, "name": "张三"}
#     return ok_no_store(response, user)
#
# 响应头会包含：Cache-Control: no-store
# 响应体会是：{"data": {"id": 1, "name": "张三"}}