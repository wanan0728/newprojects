# 1.6 app/core/errors.py
# 自定义异常处理模块
#
# 这个文件定义了项目自己的异常类和相关工具函数。
# 主要作用是在业务代码中统一抛出错误，然后由全局异常处理器捕获并返回给客户端。

# 这行导入允许在类型提示中使用还没定义的类名，比如类A的方法返回类型可以是A本身
from __future__ import annotations

# 从dataclasses模块导入dataclass装饰器，这个装饰器可以自动为类生成__init__等方法
from dataclasses import dataclass

# 从typing模块导入类型提示工具：Any表示任意类型，Mapping表示映射类型（如字典），NoReturn表示函数不会正常返回
from typing import Any, Mapping, NoReturn

# 从项目的错误码模块导入错误消息和HTTP状态码的配置字典
from app.core.error_codes import ERROR_MESSAGES, ERROR_STATUS


# 这行是装饰器，告诉Python这个类要自动生成__init__等方法
@dataclass
# 定义自定义异常类，继承Python内置的Exception类，这样它就可以被raise抛出
class AppError(Exception):
    # 错误码属性，字符串类型，必填项，用于标识错误类型
    code: str
    # HTTP状态码属性，整数类型，默认值是400（客户端请求错误）
    http_status: int = 400
    # 错误消息属性，可以是字符串或者None，默认为None，用于给用户看的错误提示
    message: str | None = None
    # 额外数据属性，可以是字典或者None，默认为None，用于传递调试信息等额外数据
    meta: dict[str, Any] | None = None

    # 这是dataclass初始化后自动调用的方法，双下划线包围表示这是Python内部使用的方法
    def __post_init__(self) -> None:
        # 调用父类Exception的初始化方法，传入错误消息或错误码作为异常的描述信息
        Exception.__init__(self, self.message or self.code)


# 定义函数：根据错误码解析出对应的错误消息
def resolve_message(code: str, default: str | None = None) -> str:
    # 将错误码转换为字符串，如果是None则转为空字符串，然后去掉首尾空格
    c = str(code or "").strip()
    # 如果处理后的错误码是空字符串
    if not c:
        # 返回默认值，如果默认值是None则返回空字符串
        return str(default or "")
    # 从错误消息配置字典中根据错误码获取对应的消息
    msg = ERROR_MESSAGES.get(c)
    # 如果找到了对应的消息
    if msg is not None:
        # 将该消息转换为字符串并返回
        return str(msg)
    # 如果没找到，返回默认值，默认值为None则返回错误码本身
    return str(default or c)


# 定义函数：创建错误对象（但不抛出）
def err(
        # 错误码参数，字符串类型，必填
        code: str,
        # *号表示后面的参数必须用关键字方式传递，比如http_status=404
        *,
        # HTTP状态码参数，可以是整数或None，默认None表示从配置中获取
        http_status: int | None = None,
        # 错误消息参数，可以是字符串或None，默认None表示从配置中获取
        message: str | None = None,
        # 额外数据参数，可以是任何映射类型（如字典）或None，默认None
        meta: Mapping[str, Any] | None = None,
        # -> AppError 表示这个函数返回一个AppError对象
) -> AppError:
    # 将错误码转换为字符串，确保它是字符串类型
    c = str(code)

    # 处理HTTP状态码：如果传入了http_status，就使用它并转为整数；否则从配置字典中根据错误码获取，获取不到就用400
    st = int(http_status) if http_status is not None else int(ERROR_STATUS.get(c, 400))

    # 声明一个变量，用于存储处理后的meta数据，类型是字典或None
    meta_dict: dict[str, Any] | None
    # 如果没有传入meta数据
    if meta is None:
        # 将meta_dict设为None
        meta_dict = None
    # 如果传入的meta已经是字典类型
    elif isinstance(meta, dict):
        # 直接使用这个字典
        meta_dict = meta
    # 如果传入的meta是其他类型（比如元组列表）
    else:
        # 强制将其转换为字典
        meta_dict = dict(meta)

    # 处理错误消息：如果传入了message，就用传入的；否则调用resolve_message从配置中获取，获取不到就用错误码
    msg = message if message is not None else resolve_message(c, c)

    # 创建并返回一个AppError对象，传入处理好的错误码、HTTP状态码、错误消息和meta数据
    return AppError(code=c, http_status=st, message=msg, meta=meta_dict)


# 定义函数：抛出错误异常
def raise_err(
        # 错误码参数，字符串类型，必填
        code: str,
        # *号表示后面的参数必须用关键字方式传递
        *,
        # HTTP状态码参数，可选
        http_status: int | None = None,
        # 错误消息参数，可选
        message: str | None = None,
        # 额外数据参数，可选
        meta: Mapping[str, Any] | None = None,
        # -> NoReturn 表示这个函数永远不会正常返回，一定会抛出异常
) -> NoReturn:
    # 调用err函数创建错误对象，然后立即抛出这个异常
    raise err(code, http_status=http_status, message=message, meta=meta)