# 4.11 app/api/middleware/tenant.py
# 租户上下文中间件模块
#
# 这也是一个中间件，用来在请求中解析出workspace id（租户ID）。
# 我们这个项目没有workspace id，很多操作是无法继续的，所以我们会从3个位置尝试获取并解析WORKSPACE_ID。
# 这三个地方分别是：
#   1. 请求头中叫X-Workspace-Id
#   2. query中通过参数携带workspace_id
#   3. url中自带/workspace/{id} 或 /workspaces/{id}

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入re模块，用于正则表达式匹配URL路径
import re

# 从fastapi导入Request类，用于获取请求信息
from fastapi import Request
# 从starlette.middleware.base导入BaseHTTPMiddleware，用于创建中间件
from starlette.middleware.base import BaseHTTPMiddleware

# 从请求上下文模块导入设置工作空间ID的函数
from app.core.request_context import set_workspace_id

# 定义请求头中存放workspace id的字段名
# request中放的workspace id的名字
_HDR_WORKSPACE_ID = "X-Workspace-Id"

# 下面两个正则表达式是为了验证url中是否符合规范，我们这里的规范是/workspace/{id}或者/workspaces/{id}
# 正则表达式解释：
#   /workspaces/(\d+) 匹配 /workspaces/123
#   (?:/|$) 表示后面要么是斜杠，要么是字符串结尾
#   (\d+) 捕获组，提取数字部分
_RE_WS_PATH = re.compile(r"/workspaces/(\d+)(?:/|$)")
_RE_WS_PATH2 = re.compile(r"/workspace/(\d+)(?:/|$)")


# 定义_to_int函数，将传入的对象尽量转换为整数
# v: object 传入的对象，可以是各种类型
# -> int | None 返回整数或None
def _to_int(v: object) -> int | None:
    """
    将传入的参数尽量转成int

    支持的类型：
    - None: 返回None
    - 字符串: 尝试转换为整数
    - 字节串: 先解码为UTF-8，再转换
    - 其他: 转字符串后再转换
    转换失败返回None
    """
    # 如果v是None，直接返回None
    if v is None:
        return None

    # 如果v是字节类型（bytes、bytearray）
    if isinstance(v, (bytes, bytearray)):
        try:
            # 尝试用UTF-8解码为字符串
            v = v.decode("utf-8")
        except Exception:
            # 解码失败返回None
            return None

    # 尝试将v转换为整数
    try:
        # 先转字符串，去掉首尾空格，再转整数
        return int(str(v).strip())
    except Exception:
        # 转换失败返回None
        return None


# 定义_extract_from_path函数，从URL路径中解析出workspace id
# path: str URL路径
# -> int | None 返回整数或None
def _extract_from_path(path: str) -> int | None:
    """
    从URL中解析出/workspace/{id}或者/workspaces/{id}里面的id

    例如：
    - /workspaces/123 → 返回123
    - /workspaces/123/users → 返回123
    - /workspace/456 → 返回456
    - /other/path → 返回None
    """
    # 使用第一个正则表达式匹配 /workspaces/{id}
    m = _RE_WS_PATH.search(path or "")
    if m:
        try:
            # group(1)获取第一个捕获组，即数字部分
            v = int(m.group(1))
            # 只返回正数（ID应该大于0）
            return v if v > 0 else None
        except Exception:
            return None

    # 使用第二个正则表达式匹配 /workspace/{id}
    m = _RE_WS_PATH2.search(path or "")
    if m:
        try:
            v = int(m.group(1))
            return v if v > 0 else None
        except Exception:
            return None

    # 都没匹配上，返回None
    return None


# 定义_extract_workspace_id函数，从请求中获取workspace_id
# request: Request 请求对象
# -> int | None 返回整数或None
def _extract_workspace_id(request: Request) -> int | None:
    """
    从请求中获取workspace_id，按优先级从三个位置尝试：
    1. 请求头 X-Workspace-Id
    2. 查询参数 workspace_id
    3. URL路径中的 /workspace/{id} 或 /workspaces/{id}
    """
    # 从请求头中获取
    wid = _to_int(request.headers.get(_HDR_WORKSPACE_ID))
    if wid and wid > 0:
        return int(wid)

    # 从查询参数中获取 http://xxx/xxx?workspace_id=1
    wid = _to_int(request.query_params.get("workspace_id"))
    if wid and wid > 0:
        return int(wid)

    # 从URL路径中获取 http://xxx/xxx/workspace/1 或 /workspaces/1
    wid = _extract_from_path(request.url.path)
    if wid and wid > 0:
        return int(wid)

    # 都没找到，返回None
    return None


# 定义TenantContextMiddleware类，继承自BaseHTTPMiddleware
# 这个中间件负责提取并设置租户上下文
class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    租户上下文中间件

    在请求处理前：
    - 从请求头、查询参数、URL路径中提取workspace_id
    - 存入request.state
    - 设置到上下文变量

    这样后续的数据库操作、审计日志等都可以获取当前租户ID。
    """

    # 重写dispatch方法，这是中间件的核心方法
    # request: Request 请求对象
    # call_next: 调用下一个中间件或路由处理函数
    async def dispatch(self, request: Request, call_next):
        # 从请求中提取workspace_id
        wid = _extract_workspace_id(request)

        # 将workspace_id存入request.state，方便其他中间件使用
        setattr(request.state, "workspace_id", wid)

        # 将workspace_id设置到上下文变量，方便整个请求周期使用
        set_workspace_id(wid)

        # 调用下一个中间件或路由处理函数
        return await call_next(request)