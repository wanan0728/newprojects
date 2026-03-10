# 7.2 app/modules/authz/scope_keys.py
# 权限作用域键生成与解析模块
#
# scope_key 是一个权限字符串，用于表示权限生效的范围。
# 格式示例：
#   - workspace:2                  （工作空间级别）
#   - project:4                     （项目级别）
#   - resource:doc:100              （具体资源级别，如文档ID 100）
#   - global                         （全局级别，表示所有范围）
# 该模块提供生成各种作用域键的函数，以及解析作用域键的工具。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样可以在类型提示中使用尚未定义的类，避免循环引用
from __future__ import annotations

# 从dataclasses模块导入dataclass装饰器，用于定义数据类
# dataclass 可以自动生成 __init__、__repr__ 等方法，简化类的定义
from dataclasses import dataclass

# 导入全局作用域常量（从 consts 模块，但这里直接定义了一个同名常量，可能后续会替换）
# 这里直接定义了 SCOPE_GLOBAL，与 consts 模块保持一致
SCOPE_GLOBAL = "global"

# 定义各作用域前缀常量，用于构建作用域键
# 前缀加具体 ID 组成完整的 scope_key
_PREFIX_WORKSPACE = "workspace:"  # 工作空间前缀
_PREFIX_PROJECT = "project:"  # 项目前缀
_PREFIX_RESOURCE = "resource:"  # 资源前缀

# 定义 scope_key 的最大长度常量，用于验证输入合法性
_MAX_LEN = 128  # scope_key的最大长度


# 定义 scope_global 函数，返回全局作用域字符串
def scope_global() -> str:
    """
    返回全局作用域键

    返回:
        "global" 字符串
    """
    return SCOPE_GLOBAL


# 定义 scope_workspace 函数，生成工作空间级别的作用域键
def scope_workspace(workspace_id: int) -> str:
    """
    生成工作空间作用域键

    参数:
        workspace_id: 工作空间ID

    返回:
        格式为 "workspace:{id}" 的字符串
    """
    # 使用 f-string 将前缀和整数 ID 拼接
    # int(workspace_id) 确保参数为整数类型
    return f"{_PREFIX_WORKSPACE}{int(workspace_id)}"


# 定义 scope_project 函数，生成项目级别的作用域键
def scope_project(project_id: int) -> str:
    """
    生成项目作用域键

    参数:
        project_id: 项目ID

    返回:
        格式为 "project:{id}" 的字符串
    """
    return f"{_PREFIX_PROJECT}{int(project_id)}"


# 定义 scope_resource 函数，生成资源级别的作用域键
def scope_resource(resource_type: str, ref_id: int) -> str:
    """
    生成资源作用域键

    参数:
        resource_type: 资源类型，如 "doc", "audio" 等
        ref_id: 资源在业务表中的主键ID

    返回:
        格式为 "resource:{type}:{id}" 的字符串

    抛出:
        ValueError: 如果资源类型无效（空字符串或包含冒号）
    """
    # 去除 resource_type 首尾空格，并转换为字符串
    rt = str(resource_type or "").strip()
    # 如果资源类型为空，抛出异常
    if not rt:
        raise ValueError("bad_resource_type")
    # 如果资源类型中包含冒号，会导致解析歧义，因此禁止
    if ":" in rt:
        raise ValueError("bad_resource_type")
    # 拼接资源作用域键
    return f"{_PREFIX_RESOURCE}{rt}:{int(ref_id)}"


# 定义 ParsedScope 数据类，用于表示解析后的作用域结构体
@dataclass(frozen=True)  # frozen=True 使实例不可变，类似于只读对象
class ParsedScope:
    """
    解析后的作用域键结构体

    属性:
        kind: 作用域类型，可以是 "global", "workspace", "project", "resource"
        workspace_id: 工作空间ID，仅当 kind 为 workspace 或 resource 时可能包含
        project_id: 项目ID，仅当 kind 为 project 或 resource 时可能包含
        resource_type: 资源类型，仅当 kind 为 resource 时有效
        ref_id: 资源ID，仅当 kind 为 resource 时有效
    """
    kind: str  # 资源的种类，比如 doc、audio 等等，是这个意思
    workspace_id: int | None = None  # 工作空间ID，可选
    project_id: int | None = None  # 项目ID，可选
    resource_type: str | None = None  # 资源类型，可选
    ref_id: int | None = None  # 资源在关系数据库中的id，可选


# 定义 parse_scope_key 函数，将 scope_key 字符串解析为 ParsedScope 对象
def parse_scope_key(scope_key: str) -> ParsedScope:
    """
    解析作用域键字符串，返回结构化的 ParsedScope 对象

    参数:
        scope_key: 作用域键字符串，如 "workspace:2", "resource:doc:100"

    返回:
        对应的 ParsedScope 对象

    抛出:
        ValueError: 如果格式错误或超出长度限制
    """
    # 去除首尾空格，并转换为字符串，若为 None 则转为空字符串
    sk = str(scope_key or "").strip()
    # 如果为空或超过最大长度，抛出异常
    if not sk or len(sk) > _MAX_LEN:
        raise ValueError("bad_scope_key")

    # 情况1：全局作用域
    if sk == SCOPE_GLOBAL:
        # 返回 kind="global" 的 ParsedScope，其他字段均为默认 None
        return ParsedScope(kind="global")

    # 情况2：工作空间作用域
    if sk.startswith(_PREFIX_WORKSPACE):
        # 截取前缀之后的部分，应该是一个数字 ID
        v = sk[len(_PREFIX_WORKSPACE):]
        # 尝试转换为整数，如果失败会自动抛出 ValueError
        return ParsedScope(kind="workspace", workspace_id=int(v))

    # 情况3：项目作用域
    if sk.startswith(_PREFIX_PROJECT):
        v = sk[len(_PREFIX_PROJECT):]
        return ParsedScope(kind="project", project_id=int(v))

    # 情况4：资源作用域
    if sk.startswith(_PREFIX_RESOURCE):
        # 去掉资源前缀后，剩余部分应为 "resource_type:ref_id"
        rest = sk[len(_PREFIX_RESOURCE):]
        # 检查是否包含冒号，若不包含则格式错误
        if ":" not in rest:
            raise ValueError("bad_scope_key")
        # 用第一个冒号分割，得到资源类型和资源ID
        rt, rid = rest.split(":", 1)
        rt = rt.strip()
        # 验证资源类型不能为空且不能包含冒号
        if not rt or ":" in rt:
            raise ValueError("bad_scope_key")
        # 返回解析后的 ParsedScope，kind 为 "resource"
        return ParsedScope(kind="resource", resource_type=rt, ref_id=int(rid))

    # 如果以上都不匹配，抛出异常
    raise ValueError("bad_scope_key")


# 定义 scopes_with_global 函数，用于在权限查询时包含全局授权
def scopes_with_global(scope_key: str) -> list[str]:
    """
    给定一个 scope_key，返回当前作用域键和全局作用域键的列表。
    用于权限查询时，需要同时检查当前作用域和全局作用域的授权情况。

    参数:
        scope_key: 当前的作用域键，可能为空字符串

    返回:
        包含一个或两个元素的列表：
            - 如果 scope_key 为空或本身就是 global，返回 [SCOPE_GLOBAL]
            - 否则返回 [scope_key, SCOPE_GLOBAL]
    """
    # 去除首尾空格，空字符串处理
    sk = str(scope_key or "").strip()
    # 如果为空，直接返回只包含全局的列表
    if not sk:
        return [SCOPE_GLOBAL]
    # 如果已经是全局，同样返回只包含全局的列表
    if sk == SCOPE_GLOBAL:
        return [SCOPE_GLOBAL]
    # 否则返回当前作用域键和全局键，表示在查询权限时同时考虑这两个范围
    return [sk, SCOPE_GLOBAL]