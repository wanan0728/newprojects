# 1.4 app/core/api_response.py
# 接口响应格式化工具
#
# 这个文件就干一件事：把接口返回的数据包装成统一的格式。
# 不管返回什么数据，都用这个函数包一下，保证所有接口返回格式一致。


# 让类型提示更好用，支持在类型注解中使用还没定义的类名
from __future__ import annotations

# 导入Any，表示"任意类型"，因为接口可以返回任何数据
from typing import Any

# Pydantic的模型基类，用来判断传入的参数是不是Pydantic模型
from pydantic import BaseModel

# 导入我们自己定义的元数据模型
from app.core.api_schemas import Meta


def ok(data: Any, meta: dict[str, Any] | Meta | None = None) -> dict:
    """
    包装成功响应的数据

    参数:
        data: 要返回的数据，可以是任何东西（字符串、数字、列表、字典...）
        meta: 额外的元数据，比如分页信息、统计信息等（不是必填）

    返回:
        包装好的字典，格式固定为 {"data": 实际数据, "meta": 元数据} 或 {"data": 实际数据}

    举个栗子:
        >>> ok({"name": "张三"})
        {"data": {"name": "张三"}}

        >>> ok(["苹果", "香蕉"], {"total": 2, "page": 1})
        {"data": ["苹果", "香蕉"], "meta": {"total": 2, "page": 1}}
    """
    # 情况1：没有元数据，直接返回数据
    if meta is None:
        return {"data": data}

    # 情况2：元数据是我们定义的Meta对象，把它转成字典
    if isinstance(meta, Meta):
        return {"data": data, "meta": meta.model_dump()}

    # 情况3：元数据是任意Pydantic模型，也转成字典
    # 这样更灵活，可以用任何现成的模型当元数据
    if isinstance(meta, BaseModel):
        return {"data": data, "meta": meta.model_dump()}

    # 情况4：元数据是字典或者其他能转成字典的东西
    # 强制转成字典，保证格式统一
    return {"data": data, "meta": dict(meta)}