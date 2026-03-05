# 3.5 app/modules/audit/hook.py
# 审计功能钩子模块
#
# 这个文件是一个"钩子"（hook），用于延迟加载审计功能的具体实现。
# 它的作用是在不强制依赖审计模块的情况下提供审计接口，
# 避免循环导入问题，同时允许在审计模块未加载时优雅降级（无操作）。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从typing模块导入类型提示工具
from typing import Any, Awaitable, Callable, cast

# 定义全局变量，用于存储实际审计函数的引用
# _record_impl: 存储实际记录审计事件的函数，可以是None或函数
_record_impl: Callable[..., Any] | None = None

# _init_impl: 存储实际初始化审计上下文的函数，可以是None或函数
_init_impl: Callable[[], Any] | None = None

# _flush_impl: 存储实际刷新审计事件到数据库的函数，可以是None或异步函数
_flush_impl: Callable[[Any, Any], Awaitable[Any]] | None = None

# 标记是否已经尝试解析过记录函数，避免重复尝试
_resolved_record: bool = False

# 标记是否已经尝试解析过中间件函数，避免重复尝试
_resolved_mw: bool = False


# 定义_resolve_record函数，用于解析并获取记录审计事件的函数
# -> Callable[..., Any] | None 返回记录函数或None
def _resolve_record() -> Callable[..., Any] | None:
    # 声明使用全局变量
    global _record_impl, _resolved_record

    # 如果已经解析过，直接返回之前的结果
    if _resolved_record:
        return _record_impl

    # 标记为已解析
    _resolved_record = True

    # 尝试导入实际的记录函数
    try:
        # 从审计服务模块导入record函数
        from app.modules.audit.service import record as impl
        # 使用cast进行类型转换，让类型检查器满意
        _record_impl = cast(Callable[..., Any], impl)
    except Exception:
        # 如果导入失败（比如模块不存在），将实现设为None
        _record_impl = None

    # 返回解析结果
    return _record_impl


# 定义record函数，这是对外暴露的记录审计事件的接口
# 参数和app/modules/audit/service.py中的record函数完全一样
def record(
        *,
        action: str,
        status: str = "ok",
        http_status: int | None = None,
        scope_key: str | None = None,
        resource_type: str | None = None,
        resource_ref_id: int | None = None,
        actor_user_id: int | None = None,
        meta: Any | None = None,
        error_code: str | None = None,
) -> None:
    # 解析获取实际的实现函数
    impl = _resolve_record()

    # 如果没有实现（导入失败），直接返回，什么都不做
    if impl is None:
        return

    # 调用实际的实现函数，传入所有参数
    impl(
        action=action,
        status=status,
        http_status=http_status,
        scope_key=scope_key,
        resource_type=resource_type,
        resource_ref_id=resource_ref_id,
        actor_user_id=actor_user_id,
        meta=meta,
        error_code=error_code,
    )


# 定义_resolve_middleware函数，用于解析并获取中间件相关的函数
# -> tuple[Callable[[], Any], Callable[[Any, Any], Awaitable[Any]]]
#    返回一个元组，包含初始化函数和刷新函数
def _resolve_middleware() -> tuple[Callable[[], Any], Callable[[Any, Any], Awaitable[Any]]]:
    # 声明使用全局变量
    global _init_impl, _flush_impl, _resolved_mw

    # 如果已经解析过，并且两个实现都不为None，直接返回之前的结果
    if _resolved_mw and _init_impl is not None and _flush_impl is not None:
        return _init_impl, _flush_impl

    # 标记为已解析
    _resolved_mw = True

    # 尝试导入实际的中间件函数
    try:
        # 从审计中间件模块导入flush_audit和init_audit函数
        from app.modules.audit.middleware import flush_audit as _flush
        from app.modules.audit.middleware import init_audit as _init

        # 使用cast进行类型转换
        _init_impl = cast(Callable[[], Any], _init)
        _flush_impl = cast(Callable[[Any, Any], Awaitable[Any]], _flush)
    except Exception:
        # 如果导入失败，定义空操作函数（什么都不做的函数）

        # 定义空操作的初始化函数
        def _noop_init() -> None:
            return None

        # 定义空操作的刷新函数
        async def _noop_flush(_request: Any, _response: Any) -> None:
            return None

        # 将实现设为这些空操作函数
        _init_impl = _noop_init
        _flush_impl = _noop_flush

    # 返回初始化函数和刷新函数
    return _init_impl, _flush_impl


# 定义init_audit函数，对外暴露的初始化审计上下文的接口
def init_audit() -> None:
    # 解析获取初始化函数（元组的第一个元素）
    init_fn, _ = _resolve_middleware()
    # 调用初始化函数
    init_fn()


# 定义flush_audit函数，对外暴露的刷新审计事件到数据库的接口
# request: Any 请求对象
# response: Any 响应对象
async def flush_audit(request: Any, response: Any) -> None:
    # 解析获取刷新函数（元组的第二个元素）
    _, flush_fn = _resolve_middleware()
    # 调用刷新函数
    await flush_fn(request, response)


# 这个代码块只在直接运行这个文件时执行，不会在导入时执行
if __name__ == '__main__':
    # 测试代码：打印init_audit()的返回值（实际上是None）
    print(init_audit())