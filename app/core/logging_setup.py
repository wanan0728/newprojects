# 1.9 app/core/logging_setup.py
# 日志系统配置模块
#
# 这个文件主要是对Python自带的日志库按照我们的要求进行设置。
# 它定义了日志的格式（JSON格式）、自动添加请求ID和用户ID、敏感信息脱敏等功能，
# 确保日志记录统一、安全、便于后续分析和排查问题。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 导入dataclasses模块，用于处理数据类（@dataclass）
# 需要用它来判断对象是否是数据类，以及将数据类转为字典
import dataclasses
# 导入json模块，用于将日志转换为JSON格式
import json
# 导入logging模块，Python标准日志库
import logging
# 从datetime模块导入date和datetime，用于处理日期时间类型的序列化
from datetime import date, datetime
# 从logging.config导入dictConfig，用于通过字典配置日志系统
from logging.config import dictConfig
# 从typing导入Any，表示任意类型
from typing import Any

# 从pydantic导入BaseModel，用于判断对象是否是Pydantic模型
from pydantic import BaseModel

# 从项目的脱敏模块导入redact_obj函数，用于过滤敏感信息
from app.core.redaction import redact_obj
# 从请求上下文模块导入get_request_id和get_user_id函数
# 用于在日志中自动添加请求ID和用户ID
from app.core.request_context import get_request_id, get_user_id

# 定义JSON最大嵌套深度常量
# 当处理嵌套数据结构时，超过这个深度就不再继续处理，防止无限递归
# 比如 {'k1':{'k2':{'k3':{'k4':{...}}}}}
_MAX_JSON_DEPTH = 6

# 定义字符串最大长度常量
# 日志每一行最大的长度，超过这个长度就截断，防止日志过大
_MAX_STR_LEN = 8192


# 定义ContextFilter类，继承自logging.Filter
# logging.Filter是Python自带日志库中的过滤器基类
# 过滤器的作用是在日志记录被处理前，可以修改日志记录的内容
class ContextFilter(logging.Filter):
    # 定义filter方法，这是过滤器的主要方法
    # record: logging.LogRecord 是日志记录对象，包含了日志的所有信息
    # -> bool 返回True表示这条日志应该被处理，返回False表示丢弃
    def filter(self, record: logging.LogRecord) -> bool:
        # 尝试从日志记录中获取request_id属性
        # getattr(record, "request_id", None) 如果record有request_id属性就获取，没有就返回None
        rid = getattr(record, "request_id", None)

        # 尝试从日志记录中获取user_id属性
        uid = getattr(record, "user_id", None)
        # 以上2行是从日志的每一行输出中尝试取request_id和user_id

        # 如果没有找到request_id
        if not rid:
            # 从请求上下文中获取request_id
            rid2 = get_request_id()
            # 如果获取到了
            if rid2:
                # 将request_id添加到日志记录中
                # setattr(record, "request_id", rid2) 给record对象添加request_id属性
                setattr(record, "request_id", rid2)
                # 这里就是在日志条目中补充好request_id

        # 如果没有找到user_id（注意判断条件是uid is None，而不是not uid，因为user_id可能是0）
        if uid is None:
            # 从请求上下文中获取user_id
            uid2 = get_user_id()
            # 如果获取到了
            if uid2 is not None:
                # 将user_id添加到日志记录中
                setattr(record, "user_id", uid2)
                # 这里就是在日志条目中补充好user_id

        # 我们之所以这么做，就是希望日志里一定要有请求id和用户id，这样日志才有价值

        # 返回True，表示这条日志应该被处理
        return True


# 定义_safe_str函数，用于安全地处理字符串
# s: str 输入字符串
# -> str 返回处理后的字符串
def _safe_str(s: str) -> str:
    # 如果s不是字符串类型，转换为字符串
    if not isinstance(s, str):
        s = str(s)
    # 如果字符串长度超过最大长度限制
    if len(s) > _MAX_STR_LEN:
        # 截取前_MAX_STR_LEN个字符，并添加截断标记
        return s[:_MAX_STR_LEN] + "...(truncated)"
    # 如果没有超过限制，直接返回原字符串
    return s


# 定义_bytes_to_text函数，将字节数据转换为文本
# b: bytes 输入字节数据
# -> str 返回UTF-8字符串
def _bytes_to_text(b: bytes) -> str:
    try:
        # 尝试用UTF-8解码字节数据
        return b.decode("utf-8")
    except UnicodeDecodeError:
        # 如果解码失败，返回字节数据的安全表示
        # repr(b) 返回字节的Python表示形式，比如 b'\\x00\\x01'
        return _safe_str(repr(b))


# 定义_to_jsonable函数，将任意对象转换为可JSON序列化的格式
# obj: Any 输入对象，可以是int、bool、dict、BaseModel、set、list等各种类型
# _depth: int = 0 内部参数，用于跟踪递归深度，默认为0
# -> Any 返回可JSON序列化的对象
def _to_jsonable(obj: Any, *, _depth: int = 0) -> Any:
    # 将参数(可能是int，bool，dict，BaseMode，set，list等等等)变成JSON

    # 如果递归深度超过最大限制
    if _depth > _MAX_JSON_DEPTH:
        # 返回截断标记，防止无限递归
        return "...(max_depth)"

    # 如果对象是None
    if obj is None:
        return None

    # 如果对象是布尔、整数、浮点数，直接返回（这些类型本身就是JSON可序列化的）
    if isinstance(obj, (bool, int, float)):
        return obj

    # 如果对象是字符串，进行安全截断处理
    if isinstance(obj, str):
        return _safe_str(obj)

    # 如果对象是字节类型（bytes、bytearray、memoryview）
    if isinstance(obj, (bytes, bytearray, memoryview)):
        # 将字节数据转换为文本
        return _bytes_to_text(bytes(obj))

    # 如果对象是日期时间类型
    if isinstance(obj, (datetime, date)):
        # 转换为ISO格式字符串（如 "2024-01-01T12:00:00"）
        return obj.isoformat()

    # 如果对象是Pydantic模型（继承自BaseModel）
    if isinstance(obj, BaseModel):
        try:
            # 将模型转换为字典（model_dump()），然后递归处理
            # _depth + 1 增加递归深度计数
            return _to_jsonable(obj.model_dump(), _depth=_depth + 1)
        except (TypeError, ValueError):
            # 如果转换失败，返回对象的字符串表示
            return _safe_str(str(obj))

    # 如果对象是数据类（使用@dataclass装饰的类）
    if dataclasses.is_dataclass(obj):
        try:
            # 将数据类转换为字典（asdict()），然后递归处理
            return _to_jsonable(dataclasses.asdict(obj), _depth=_depth + 1)
        except (TypeError, ValueError):
            # 如果转换失败，返回对象的字符串表示
            return _safe_str(str(obj))

    # 如果对象是字典
    if isinstance(obj, dict):
        # 创建一个新字典，用于存储处理后的结果
        out: dict[str, Any] = {}
        # 遍历字典的每个键值对
        for k, v in obj.items():
            # 将键转换为安全字符串
            kk = _safe_str(k)
            # 递归处理值，深度+1
            out[kk] = _to_jsonable(v, _depth=_depth + 1)
        return out

    # 如果对象是列表或元组
    if isinstance(obj, (list, tuple)):
        # 递归处理每个元素，返回新列表
        return [_to_jsonable(x, _depth=_depth + 1) for x in obj]

    # 如果对象是集合
    if isinstance(obj, set):
        # 将集合转换为列表，并递归处理每个元素
        return [_to_jsonable(x, _depth=_depth + 1) for x in obj]

    # 如果对象是异常（继承自BaseException）
    if isinstance(obj, BaseException):
        # 返回包含异常类型和消息的字典
        return {
            "type": obj.__class__.__name__,  # 异常类名
            "message": _safe_str(str(obj))  # 异常消息
        }

    # 对于其他类型，返回安全字符串表示
    return _safe_str(str(obj))


# 定义JsonFormatter类，继承自logging.Formatter
# logging.Formatter是Python自带日志库中的格式化器基类
# 用于定义日志的输出格式，这里我们指定输出为JSON格式
class JsonFormatter(logging.Formatter):
    # 定义format方法，这是格式化器的主要方法
    # record: logging.LogRecord 日志记录对象
    # -> str 返回格式化后的日志字符串
    def format(self, record: logging.LogRecord) -> str:
        # 创建基础日志负载字典
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),  # 日志级别（小写）
            "logger": record.name,  # 日志记录器名称
            "message": record.getMessage(),  # 日志消息
        }

        # 获取请求ID：优先从日志记录中获取，没有则从上下文获取
        rid = getattr(record, "request_id", None) or get_request_id()

        # 获取用户ID：从日志记录中获取
        uid = getattr(record, "user_id", None)
        # 如果日志记录中没有用户ID
        if uid is None:
            # 从上下文中获取用户ID
            uid = get_user_id()

        # 如果请求ID存在，添加到负载中
        if rid:
            payload["request_id"] = rid

        # 如果用户ID存在，添加到负载中
        if uid is not None:
            payload["user_id"] = uid

        # 如果日志记录中有异常信息
        if record.exc_info:
            # 使用父类的formatException方法格式化异常信息
            payload["exc_info"] = self.formatException(record.exc_info)

        # 遍历日志记录的所有属性
        for k, v in record.__dict__.items():
            # 跳过Python日志库自带的标准属性
            if k in {
                "name",  # 日志记录器名称
                "msg",  # 原始消息
                "args",  # 消息参数
                "levelname",  # 日志级别名
                "levelno",  # 日志级别号
                "pathname",  # 文件路径
                "filename",  # 文件名
                "module",  # 模块名
                "exc_info",  # 异常信息
                "exc_text",  # 异常文本
                "stack_info",  # 堆栈信息
                "lineno",  # 行号
                "funcName",  # 函数名
                "created",  # 创建时间
                "msecs",  # 毫秒数
                "relativeCreated",  # 相对创建时间
                "thread",  # 线程ID
                "threadName",  # 线程名
                "processName",  # 进程名
                "process",  # 进程ID
            }:
                continue
            # 如果这个键已经在payload中，跳过
            if k in payload:
                continue
            # 将其他自定义属性添加到payload中
            payload[k] = v

        # 将payload转换为可JSON序列化的格式
        safe_payload = _to_jsonable(payload)
        # 对敏感信息进行脱敏处理
        safe_payload = redact_obj(safe_payload)

        try:
            # 尝试将payload转换为JSON字符串
            # ensure_ascii=False 允许输出非ASCII字符（如中文）
            return json.dumps(safe_payload, ensure_ascii=False)
        except (TypeError, ValueError, OverflowError):
            # 如果JSON序列化失败，创建降级使用的备用日志
            fallback = {
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": _safe_str(record.getMessage()),
                "request_id": rid,
                "user_id": uid,
                "format_error": True,  # 标记格式化出错
            }
            # 对备用日志也进行脱敏和JSON序列化
            return json.dumps(redact_obj(_to_jsonable(fallback)), ensure_ascii=False)


# 定义setup_logging函数，用于配置日志系统
# level: str = "INFO" 日志级别，默认INFO
# -> None 无返回值
def setup_logging(*, level: str = "INFO") -> None:
    # 这段才是真正的日志设置，比如用上之前的过滤器和格式化器

    # 处理日志级别：如果level为None则用"INFO"，并转为大写
    level = (level or "INFO").upper()

    # 定义日志配置字典
    cfg = {
        "version": 1,  # 配置文件版本号，必须是1
        "disable_existing_loggers": False,  # 不禁用已有的日志记录器
        "filters": {  # 定义过滤器
            "context": {"()": "app.core.logging_setup.ContextFilter"},  # 使用ContextFilter类
        },
        "formatters": {  # 定义格式化器
            "json": {"()": "app.core.logging_setup.JsonFormatter"},  # 使用JsonFormatter类
        },
        "handlers": {  # 定义处理器
            "stdout": {  # 标准输出处理器
                "class": "logging.StreamHandler",  # 输出到控制台
                "formatter": "json",  # 使用json格式化器
                "filters": ["context"],  # 使用context过滤器
                "level": level,  # 设置日志级别
            }
        },
        "root": {  # 根日志记录器配置
            "handlers": ["stdout"],  # 使用stdout处理器
            "level": level,  # 设置日志级别
        },
        "loggers": {  # 其他特定日志记录器的配置
            "uvicorn": {"level": level},  # uvicorn服务器日志
            "uvicorn.error": {"level": level},  # uvicorn错误日志
            "uvicorn.access": {  # uvicorn访问日志
                "level": level,
                "propagate": False,  # 不向父日志记录器传递
                "handlers": ["stdout"],  # 使用stdout处理器
            },
            "access": {  # 自定义访问日志
                "level": level,
                "propagate": False,
                "handlers": ["stdout"],
            },
        },
    }

    # 使用dictConfig应用配置
    dictConfig(cfg)