# 3.1 app/modules/audit/context.py
# 审计日志上下文管理模块
#
# 这个文件使用ContextVar管理当前请求的审计事件列表。
# 审计日志用于记录用户的关键操作（如创建、修改、删除），
# 方便后续追踪谁在什么时候做了什么操作。
# 通过上下文变量，可以在请求的任意地方添加审计事件，最后统一保存。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从contextvars模块导入ContextVar类
# contextvars是Python标准库，专门用于管理上下文变量
# ContextVar可以在异步任务中保持变量的上下文，不会相互干扰
from contextvars import ContextVar

# 从typing模块导入Any类型
# Any表示任意类型，因为审计事件的值可以是任何类型
from typing import Any

# 定义一个ContextVar变量，名为_audit_events，用于存储当前请求的审计事件列表
# ContextVar("audit_events") 创建了一个名为"audit_events"的上下文变量
# list[dict[str, Any]] | None 表示这个变量可以存储审计事件列表，也可以是None
#   - 列表中的每个元素是一个字典，键是字符串，值是任意类型
#   - 字典示例：{"action": "create_user", "user_id": 123, "timestamp": "2024-01-01"}
# default=None 设置默认值为None，表示如果没有设置值就返回None
# 变量名前加下划线 _ 表示这是一个"私有"变量，不应该直接在外面使用
_audit_events: ContextVar[list[dict[str, Any]] | None] = ContextVar("audit_events", default=None)


# 定义init_audit_context函数，用于初始化审计上下文
# -> None 表示这个函数没有返回值
def init_audit_context() -> None:
    # 将_audit_events设置为一个空列表
    # _audit_events.set([]) 相当于 _audit_events = []
    # 这样当前请求就有了一个空的审计事件列表，可以开始添加事件
    _audit_events.set([])


# 定义clear_audit_context函数，用于清除审计上下文
# -> None 表示这个函数没有返回值
def clear_audit_context() -> None:
    # 将_audit_events设置为None
    # _audit_events.set(None) 相当于 _audit_events = None
    # 这样当前请求的审计事件列表就被清除了
    _audit_events.set(None)


# 定义add_audit_event函数，用于添加审计事件
# evt: dict[str, Any] 参数，接收一个字典类型的审计事件
# 例如：{"action": "create_user", "user_id": 123, "ip": "192.168.1.1"}
# -> None 表示这个函数没有返回值
def add_audit_event(evt: dict[str, Any]) -> None:
    # 从上下文中获取审计事件列表
    # _audit_events.get() 将审计事件的那个列表取出来
    buf = _audit_events.get()

    # 如果列表是None，说明审计上下文没有初始化
    # 直接返回，不添加事件
    if buf is None:
        return

    # 将新的事件添加到列表中
    # buf.append(evt) 在list中添加一个元素evt，即一个审计事件
    # 审计事件是一个字典，元素类型是{字符串:任意类型}
    buf.append(evt)


# 定义pop_audit_events函数，用于取出所有审计事件并清空上下文
# -> list[dict[str, Any]] 返回审计事件列表
# 这个函数的作用是将审计上下文中的东西全取出来并清空上下文
def pop_audit_events() -> list[dict[str, Any]]:
    # 从上下文中获取审计事件列表
    # _audit_events.get() 拿到之前的list
    buf = _audit_events.get()

    # 如果列表不存在或为空
    # if not buf: 判断buf是否是None或空列表
    if not buf:
        # 返回空列表
        return []

    # 创建当前列表的副本
    # list(buf) 将原列表复制一份，避免后续清空影响返回值
    out = list(buf)

    # 清空原列表
    # buf.clear() 将list清空
    buf.clear()

    # 返回复制的列表
    return out