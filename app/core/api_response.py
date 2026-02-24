# 1.4 app/core/api_response.py
# 接口响应格式化工具
#
# 这个文件就干一件事：把接口返回的数据包装成统一的格式。
# 不管返回什么数据，都用这个函数包一下，保证所有接口返回格式一致。


# 这行从__future__导入annotations功能，它允许在类型提示中直接使用类名而不用加引号
# 比如可以写 def func() -> MyClass: 而不需要写成 def func() -> "MyClass":
from __future__ import annotations

# 从typing模块导入Any类型，Any表示任意类型的值
# 因为接口可能返回字符串、数字、列表、字典等各种类型的数据，所以用Any最合适
from typing import Any

# 从pydantic导入BaseModel类，这是所有Pydantic模型的基类
# 导入它是为了判断传入的meta参数是不是Pydantic模型对象
from pydantic import BaseModel

# 从我们自己定义的api_schemas模块导入Meta类
# Meta是我们专门用来存放元数据的模型，比如分页信息、统计信息等
from app.core.api_schemas import Meta


# 定义ok函数，用于包装成功的响应数据
# def是定义函数的关键字，ok是函数名，表示"成功"的意思
# data: Any 表示第一个参数名叫data，类型是Any（任意类型）
# meta: dict[str, Any] | Meta | None = None 表示第二个参数名叫meta，可以是三种类型之一：
#   - dict[str, Any]: 键为字符串、值为任意类型的字典
#   - Meta: 我们定义的Meta模型对象
#   - None: 空值
#   = None 表示如果不传这个参数，默认就是None
# -> dict: 表示这个函数返回一个字典
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
    # if是条件判断关键字，meta is None 判断meta是不是None
    # 如果是None，说明调用者没传meta或者传了None，就不需要包装meta字段
    if meta is None:
        # 返回一个字典，只有data字段，里面放的是原始数据
        # {"data": data} 是字典的字面量写法，冒号左边是键，右边是值
        return {"data": data}

    # 情况2：元数据是我们定义的Meta对象，把它转成字典
    # isinstance(meta, Meta) 判断meta是不是Meta类的实例
    # 如果是，说明传进来的是一个Meta模型对象
    if isinstance(meta, Meta):
        # meta.model_dump() 是Pydantic模型的方法，把模型对象转成字典
        # 比如 Meta(page=1, total=10) 会变成 {"page": 1, "total": 10}
        # 然后和data一起包装成字典返回
        return {"data": data, "meta": meta.model_dump()}

    # 情况3：元数据是任意Pydantic模型，也转成字典
    # isinstance(meta, BaseModel) 判断meta是不是任何Pydantic模型的实例
    # 因为BaseModel是所有Pydantic模型的父类，所以只要是Pydantic模型都会进到这里
    # 这样更灵活，可以用任何现成的模型当元数据，不限于Meta类
    if isinstance(meta, BaseModel):
        # 同样调用model_dump()把模型转成字典
        # 比如 User(name="张三") 会变成 {"name": "张三"}
        return {"data": data, "meta": meta.model_dump()}

    # 情况4：元数据是字典或者其他能转成字典的东西
    # 执行到这里，说明meta不是None，也不是Meta对象，也不是Pydantic模型
    # 那它应该是个字典或者可以转成字典的东西（比如元组列表）
    # dict(meta) 强制把meta转换成字典，如果转不了会报错
    # 强制转成字典，保证格式统一
    return {"data": data, "meta": dict(meta)}