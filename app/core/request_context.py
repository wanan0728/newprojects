# 1.7 app/core/context.py
# 请求上下文变量管理模块
#
# 这个文件使用ContextVar（上下文变量）来存储每个请求的上下文信息。
# 主要作用是在整个请求处理过程中（包括多层函数调用）都能访问到当前请求的信息，
# 比如请求ID、用户ID、客户端IP等，而不需要显式地传递这些参数。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从contextvars模块导入ContextVar类
# contextvars是Python标准库，专门用于管理上下文变量
# ContextVar可以在异步任务中保持变量的上下文，不会相互干扰
from contextvars import ContextVar

# 定义一个ContextVar变量，名为_request_id，用于存储当前请求的请求ID
# ContextVar("request_id") 创建了一个名为"request_id"的上下文变量
# default=None 设置默认值为None，表示如果没有设置值就返回None
# str | None 表示这个变量可以存储字符串或者None
# 变量名前加下划线 _ 表示这是一个"私有"变量，不应该直接在外面使用
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

# 定义一个ContextVar变量，名为_user_id，用于存储当前请求的用户ID
# int | None 表示可以存储整数或None
_user_id: ContextVar[int | None] = ContextVar("user_id", default=None)

# 定义一个ContextVar变量，名为_client_ip，用于存储客户端的IP地址
_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)

# 定义一个ContextVar变量，名为_user_agent，用于存储客户端的User-Agent信息
_user_agent: ContextVar[str | None] = ContextVar("user_agent", default=None)

# 定义一个ContextVar变量，名为_workspace_id，用于存储当前请求的工作空间ID
# 适用于多租户系统，标识当前请求属于哪个工作空间
_workspace_id: ContextVar[int | None] = ContextVar("workspace_id", default=None)


# 定义设置请求ID的函数
# v: str | None 参数可以是字符串或None
# -> None 表示这个函数没有返回值
def set_request_id(v: str | None) -> None:
    # 调用_request_id变量的set方法，将值v设置到当前上下文中
    # 这样在当前请求的任何地方调用get_request_id都能拿到这个值
    _request_id.set(v)


# 定义获取请求ID的函数
# -> str | None 表示返回值可以是字符串或None
def get_request_id() -> str | None:
    # 调用_request_id变量的get方法，从当前上下文中获取存储的值
    # 如果没有设置过，会返回创建时指定的默认值None
    return _request_id.get()


# 定义设置用户ID的函数
def set_user_id(v: int | None) -> None:
    # 将用户ID存储到上下文中
    _user_id.set(v)


# 定义获取用户ID的函数
def get_user_id() -> int | None:
    # 从上下文中获取用户ID
    return _user_id.get()


# 定义设置客户端IP的函数
def set_client_ip(v: str | None) -> None:
    # 将客户端IP存储到上下文中
    _client_ip.set(v)


# 定义获取客户端IP的函数
def get_client_ip() -> str | None:
    # 从上下文中获取客户端IP
    return _client_ip.get()


# 定义设置User-Agent的函数
def set_user_agent(v: str | None) -> None:
    # 将User-Agent存储到上下文中
    _user_agent.set(v)


# 定义获取User-Agent的函数
def get_user_agent() -> str | None:
    # 从上下文中获取User-Agent
    return _user_agent.get()


# 定义设置工作空间ID的函数
def set_workspace_id(v: int | None) -> None:
    # 将工作空间ID存储到上下文中
    _workspace_id.set(v)


# 定义获取工作空间ID的函数
def get_workspace_id() -> int | None:
    # 从上下文中获取工作空间ID
    return _workspace_id.get()