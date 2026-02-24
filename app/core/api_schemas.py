# 1.3 app/core/api_schemas.py
# 接口数据模型定义
#
# 这个文件定义了接口返回数据的"模板"，也就是数据结构长什么样。
# 使用Pydantic模型可以自动验证数据类型，还能自动生成接口文档。


# 让类型提示更好用，支持在类型注解中使用还没定义的类名
from __future__ import annotations

# 导入类型提示相关工具
# Any: 任意类型，用于灵活的数据字段
# Generic: 让类支持泛型（可以适配不同类型的数据）
# TypeVar: 定义泛型变量
from typing import Any, Generic, TypeVar

# Pydantic的核心功能：BaseModel是所有模型的基类，ConfigDict用于配置模型
from pydantic import BaseModel, ConfigDict

# 定义一个泛型变量T，代表"任意类型"
# 这样ApiResponse就可以根据实际数据自动适配类型
T = TypeVar("T")


class Meta(BaseModel):
    """
    元数据模型 - 用来放一些"额外信息"

    比如分页信息（当前第几页、总共多少条）、统计信息（总共多少人）等
    不属于主要数据但又需要返回的信息都放这里
    """
    # 配置：允许接收未在模型中定义的字段
    # 简单说就是：传进来的字段如果模型里没定义，也照收不误
    model_config = ConfigDict(extra="allow")


class ApiResponse(BaseModel, Generic[T]):
    """
    通用响应模型 - 所有成功接口返回的数据都长这样

    使用泛型T，可以适配不同类型的数据：
    - 返回用户信息时，T就是用户模型
    - 返回文章列表时，T就是文章列表模型
    """
    data: T  # 实际要返回的数据，类型由T决定
    meta: Meta | None = None  # 附加信息（如分页），不是必须的


class Empty(BaseModel):
    """
    空响应模型 - 不需要返回数据时用这个

    比如删除操作，成功了只需要告诉客户端"ok"就行
    """
    ok: bool = True  # 操作是否成功，默认True（一般都成功才调用这个）


class ActionResult(BaseModel):
    """
    操作结果模型 - 和Empty基本一样，但名字更明确

    比如"修改密码"这种操作，不需要返回数据，只需要告诉结果
    """
    ok: bool = True  # 操作是否成功


class ErrorInfo(BaseModel):
    """
    错误信息模型 - 出错了返回什么内容

    所有错误都按这个格式返回，前端好统一处理
    """
    code: str  # 错误码，比如 "USER_NOT_FOUND"（程序看的）
    message: Any  # 错误信息，比如 "用户不存在"（用户看的）
    request_id: str  # 请求ID，用来查日志定位问题
    meta: dict[str, Any] | None = None  # 额外的错误信息，比如哪个字段错了


class ErrorResponse(BaseModel):
    """
    错误响应模型 - 错误返回的外层包装

    最终返回给前端的样子：{"error": {...}}
    和成功的 {"data": {...}} 对应
    """
    error: ErrorInfo  # 具体的错误信息