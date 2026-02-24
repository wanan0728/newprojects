# 1.3 app/core/api_schemas.py
# 接口数据模型定义
#
# 这个文件定义了接口返回数据的"模板"，也就是数据结构长什么样。
# 使用Pydantic模型可以自动验证数据类型，还能自动生成接口文档。


# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类定义中使用还没定义的类型，比如类A的方法返回类型可以是A本身
from __future__ import annotations

# 从typing模块导入类型提示相关工具
# typing是Python标准库，专门用于类型提示
from typing import Any, Generic, TypeVar
# Any: 特殊的类型，表示"任意类型"，相当于关闭了类型检查
# Generic: 一个类，用于创建泛型类（可以适配不同类型数据的类）
# TypeVar: 一个函数，用于定义类型变量，这个变量可以在泛型中代表任意类型

# 从pydantic库导入核心功能
# pydantic是一个第三方库，专门用于数据验证和序列化
from pydantic import BaseModel, ConfigDict

# BaseModel: 所有Pydantic模型的基类，提供了数据验证、序列化等功能
# ConfigDict: 一个字典类，用于配置模型的行为（比如是否允许额外字段）

# 定义一个类型变量T
# TypeVar("T") 创建了一个类型变量，名字叫T，可以在泛型中代表任意类型
# 这里的T就像数学中的未知数x，可以在具体使用时被实际类型替代
T = TypeVar("T")


# 定义Meta类，继承自BaseModel，所以它是一个Pydantic模型
class Meta(BaseModel):
    """
    元数据模型 - 用来放一些"额外信息"

    比如分页信息（当前第几页、总共多少条）、统计信息（总共多少人）等
    不属于主要数据但又需要返回的信息都放这里
    """
    # 配置模型的行为
    # model_config 是Pydantic v2版本的配置属性名
    # ConfigDict 是用于配置的字典类
    # extra="allow" 表示允许模型接受未定义的额外字段
    # 简单说就是：传进来的字段如果模型里没定义，也照收不误
    # 这样Meta模型可以非常灵活地接受任何元数据，不需要预先定义所有字段
    model_config = ConfigDict(extra="allow")


# 定义ApiResponse类，继承自BaseModel和Generic[T]
# BaseModel 让它成为Pydantic模型
# Generic[T] 让它成为泛型类，可以适配不同类型的数据
class ApiResponse(BaseModel, Generic[T]):
    """
    通用响应模型 - 所有成功接口返回的数据都长这样

    使用泛型T，可以适配不同类型的数据：
    - 返回用户信息时，T就是用户模型
    - 返回文章列表时，T就是文章列表模型
    """
    # data字段，类型是泛型T
    # 冒号左边是字段名，右边是类型注解
    # T在这里是一个占位符，实际使用时会被具体类型替换
    data: T

    # meta字段，类型是 Meta | None
    # | 表示"或"，所以这个字段可以是Meta类型，也可以是None
    # = None 表示默认值是None，也就是说这个字段是可选的
    meta: Meta | None = None


# 定义Empty类，继承自BaseModel
class Empty(BaseModel):
    """
    空响应模型 - 不需要返回数据时用这个

    比如删除操作，成功了只需要告诉客户端"ok"就行
    """
    # ok字段，布尔类型，默认值是True
    # bool 表示这个字段只能是True或False
    # = True 表示如果没有传值，就默认为True
    ok: bool = True


# 定义ActionResult类，继承自BaseModel
class ActionResult(BaseModel):
    """
    操作结果模型 - 和Empty基本一样，但名字更明确

    比如"修改密码"这种操作，不需要返回数据，只需要告诉结果
    """
    # ok字段，布尔类型，默认值是True
    ok: bool = True


# 定义ErrorInfo类，继承自BaseModel
class ErrorInfo(BaseModel):
    """
    错误信息模型 - 出错了返回什么内容

    所有错误都按这个格式返回，前端好统一处理
    """
    # code字段，字符串类型，必填
    # 这是错误码，比如 "USER_NOT_FOUND"，是给程序看的，前端可以根据不同错误码做不同处理
    code: str

    # message字段，Any类型，必填
    # 这是错误信息，比如 "用户不存在"，是给用户看的
    # 用Any是因为错误信息可能是字符串，也可能是其他格式（比如包含多个错误）
    message: Any

    # request_id字段，字符串类型，必填
    # 这是请求的唯一ID，可以用来在服务器日志中定位具体是哪个请求出错了
    request_id: str

    # meta字段，字典类型，可选
    # dict[str, Any] 表示键是字符串，值是任意类型的字典
    # | None 表示也可以是None
    # = None 表示默认值是None
    # 这个字段用于存放额外的错误信息，比如表单验证时具体哪个字段错了
    meta: dict[str, Any] | None = None


# 定义ErrorResponse类，继承自BaseModel
class ErrorResponse(BaseModel):
    """
    错误响应模型 - 错误返回的外层包装

    最终返回给前端的样子：{"error": {...}}
    和成功的 {"data": {...}} 对应
    """
    # error字段，类型是ErrorInfo，必填
    # 这是具体的错误信息对象，包含了错误码、消息等详细信息
    error: ErrorInfo