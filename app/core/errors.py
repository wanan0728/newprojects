# 1.6 app/core/errors.py
# 自定义异常处理模块
#
# 这个文件定义了项目自己的异常类和相关工具函数。
# 主要作用是在业务代码中统一抛出错误，然后由全局异常处理器捕获并返回给客户端。


# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类定义中使用还没定义的类型，解决循环引用问题
from __future__ import annotations

# 从dataclasses模块导入dataclass装饰器
# dataclass是Python标准库中的一个装饰器，可以自动为类生成__init__、__repr__等方法
# 不用手动写一堆模板代码，让代码更简洁
from dataclasses import dataclass

# 从typing模块导入类型提示工具
# typing是Python标准库，专门用于类型提示
from typing import Any, Mapping, NoReturn
# Any: 特殊的类型，表示"任意类型"，相当于关闭了类型检查
# Mapping: 表示映射类型的基类（如dict、OrderedDict等），比dict更通用
# NoReturn: 特殊的返回类型，表示函数永远不会正常返回（一定会抛出异常）

# 从项目的错误码模块导入配置字典
# ERROR_MESSAGES: 错误码到错误消息的映射字典
# ERROR_STATUS: 错误码到HTTP状态码的映射字典
from app.core.error_codes import ERROR_MESSAGES, ERROR_STATUS


# 使用dataclass装饰器装饰AppError类
# @dataclass 告诉Python这个类要自动生成__init__、__repr__等方法
@dataclass
# 定义AppError类，继承自Python内置的Exception类
# 继承Exception意味着这个类可以被raise抛出，也可以被try-except捕获
class AppError(Exception):
    # code属性：字符串类型，没有默认值，所以是必填字段
    # 这个属性用于存储错误码，比如"auth.access_token_expired"
    code: str

    # http_status属性：整数类型，默认值是400
    # 400是HTTP状态码，表示"客户端请求错误"
    # 这个属性用于存储应该返回给客户端的HTTP状态码
    http_status: int = 400

    # message属性：可以是字符串或者None，默认值是None
    # 这个属性用于存储给用户看的错误提示信息
    message: str | None = None

    # meta属性：可以是字典或者None，默认值是None
    # dict[str, Any] 表示键是字符串、值是任意类型的字典
    # 这个属性用于存储额外的错误数据，比如表单验证时具体哪个字段错了
    meta: dict[str, Any] | None = None

    # 定义__post_init__方法，这是dataclass的特殊方法
    # 在__init__方法执行完后会自动调用这个方法
    def __post_init__(self) -> None:
        # 调用父类Exception的__init__方法
        # self.message or self.code: 如果有message就用message，没有就用code
        # 这样Exception的默认错误信息就是message或code
        Exception.__init__(self, self.message or self.code)


# 定义resolve_message函数，用于根据错误码获取对应的错误消息
# code: 字符串类型的错误码
# default: 可选的默认值，可以是字符串或None，默认为None
# -> str: 表示这个函数返回一个字符串
def resolve_message(code: str, default: str | None = None) -> str:
    # 处理错误码：code or "" 意思是如果code是None就用空字符串
    # str() 转换为字符串，.strip() 去掉首尾空格
    c = str(code or "").strip()

    # if not c: 判断c是否是空字符串
    # 空字符串、None、0、空列表等在条件判断中都相当于False
    if not c:
        # 如果错误码是空字符串，返回默认值
        # default or "" 意思是如果default是None就用空字符串
        # str()确保返回的是字符串类型
        return str(default or "")

    # 从ERROR_MESSAGES字典中获取错误码对应的消息
    # .get(c) 方法如果找到就返回对应的值，找不到就返回None
    msg = ERROR_MESSAGES.get(c)

    # 判断是否找到了消息
    if msg is not None:
        # 找到了，转换为字符串并返回
        return str(msg)

    # 没找到，返回默认值
    # default or c 意思是如果有默认值就用默认值，没有就用错误码本身
    return str(default or c)


# 定义err函数，用于创建AppError对象（但不抛出）
# code: 必填参数，错误码
# *: 星号表示后面的参数必须用关键字方式传递，不能只按位置传
# http_status: 可选，HTTP状态码
# message: 可选，错误消息
# meta: 可选，额外数据
# -> AppError: 表示返回一个AppError对象
def err(
        code: str,
        *,
        http_status: int | None = None,
        message: str | None = None,
        meta: Mapping[str, Any] | None = None,
) -> AppError:
    # 将错误码转换为字符串，确保它是字符串类型
    c = str(code)

    # 处理HTTP状态码：
    # 如果传入了http_status，就使用它并转为整数
    # 如果没有传入，就从ERROR_STATUS字典中根据错误码获取，获取不到就用400
    # ERROR_STATUS.get(c, 400) 意思是如果找不到c对应的值，就返回400
    st = int(http_status) if http_status is not None else int(ERROR_STATUS.get(c, 400))

    # 声明meta_dict变量，类型是dict[str, Any] | None
    # 这个变量用来存储处理后的meta数据
    meta_dict: dict[str, Any] | None

    # 如果没有传入meta数据
    if meta is None:
        # meta_dict设为None
        meta_dict = None

    # 如果传入的meta已经是dict类型
    # isinstance() 函数判断一个对象是否是指定类型
    elif isinstance(meta, dict):
        # 直接使用这个字典
        meta_dict = meta

    # 如果传入的meta是其他类型（比如列表、元组等）
    else:
        # 用dict()函数强制将其转换为字典
        # 比如传入[("key", "value")]会变成{"key": "value"}
        meta_dict = dict(meta)

    # 处理错误消息：
    # 如果传入了message，就用传入的
    # 如果没有传入，就调用resolve_message从配置中获取
    # resolve_message(c, c) 意思是如果找不到对应的消息，就用错误码本身
    msg = message if message is not None else resolve_message(c, c)

    # 创建并返回AppError对象
    # 传入处理好的code、http_status、message、meta_dict
    return AppError(code=c, http_status=st, message=msg, meta=meta_dict)


# 定义raise_err函数，用于抛出错误异常
# 参数和err函数完全一样
# -> NoReturn: 表示这个函数永远不会正常返回，一定会抛出异常
def raise_err(
        code: str,
        *,
        http_status: int | None = None,
        message: str | None = None,
        meta: Mapping[str, Any] | None = None,
) -> NoReturn:
    # 调用err函数创建AppError对象
    # err(code, http_status=http_status, message=message, meta=meta)
    # 然后用raise关键字抛出这个异常
    # raise会中断当前函数的执行，向上层抛出异常
    raise err(code, http_status=http_status, message=message, meta=meta)