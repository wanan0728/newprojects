# 7.3 app/modules/authz/seed.py
# 权限种子数据模块
#
# 这个文件里不是建立表格的语句，而是表格中要提前被插入的数据。
# 早期项目我们没有这个文件，都是用 INSERT 语句直接在数据库中插入。
# 现在将这些数据集中定义在这里，方便初始化数据库时自动填充。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从typing模块导入Final，用于定义常量类型
# Final 是一个类型提示，表示这个变量是常量，不应该被重新赋值
from typing import Final

# 定义预定义的角色列表
# ROLES 是一个包含角色名称和描述的元组，每个元素是一个 (name, description) 元组
# 使用 Final 标记为常量，类型是 tuple[tuple[str, str], ...] 表示可变长度的元组，每个元素是两个字符串的元组
ROLES: Final[tuple[tuple[str, str], ...]] = (
    # 第一个角色：所有者，拥有工作空间或项目的完全控制权
    ("owner", "Workspace/Project owner"),
    # 第二个角色：管理员，管理权限但可能没有所有者那么高级
    ("admin", "Workspace/Project admin"),
    # 第三个角色：编辑者，可以创建和更新资源，但不能删除或管理
    ("editor", "Can create/update resources"),
    # 第四个角色：查看者，只读访问
    ("viewer", "Read-only access"),
)

# 定义预定义的权限列表
# PERMISSIONS 是一个包含权限代码和描述的元组，每个元素是一个 (code, description) 元组
# 权限代码用于在代码中引用，描述用于显示
PERMISSIONS: Final[tuple[tuple[str, str], ...]] = (
    # 工作空间管理权限
    ("workspace.manage", "Manage workspace settings/members"),  # 管理工作空间设置和成员
    # 项目管理权限
    ("project.manage", "Manage projects"),                      # 管理项目
    # 文档相关权限
    ("doc.read", "Read documents"),                             # 读取文档
    ("doc.write", "Create/update documents"),                   # 创建/更新文档
    ("doc.delete", "Delete documents"),                         # 删除文档
    # 音频相关权限
    ("audio.read", "Read audio resources"),                     # 读取音频资源
    ("audio.search", "Search audio content"),                   # 搜索音频内容
    ("audio.write", "Upload/update audio"),                     # 上传/更新音频
    ("audio.delete", "Delete audio"),                           # 删除音频
    # 图片相关权限
    ("image.read", "Read images"),                              # 读取图片
    ("image.write", "Upload/update images"),                    # 上传/更新图片
    ("image.delete", "Delete images"),                          # 删除图片
    # 工单相关权限
    ("ticket.read", "Read tickets"),                            # 读取工单
    ("ticket.create", "Create tickets"),                        # 创建工单
    ("ticket.approve", "Approve tickets"),                      # 审批工单
    ("ticket.close", "Close tickets"),                          # 关闭工单
)

# 提取所有权限代码，用于后续的默认角色权限分配
# 使用列表推导式遍历 PERMISSIONS，取出每个元组的第一个元素（权限代码）
# 然后转换为元组，用 Final 标记为常量
_ALL_PERM_CODES: Final[tuple[str, ...]] = tuple(code for code, _ in PERMISSIONS)

# 定义默认角色与权限的映射关系
# DEFAULT_ROLE_PERMS 是一个字典，键为角色名称，值为该角色默认拥有的权限代码元组
DEFAULT_ROLE_PERMS: Final[dict[str, tuple[str, ...]]] = {
    # 所有者拥有所有权限
    "owner": _ALL_PERM_CODES,
    # 管理员也拥有所有权限（与所有者相同）
    "admin": _ALL_PERM_CODES,
    # 编辑者拥有创建、更新资源的权限，但没有删除和管理权限
    "editor": (
        "doc.read",        # 文档读取权限
        "doc.write",       # 文档写入权限
        "audio.read",      # 音频读取权限
        "audio.search",    # 音频搜索权限
        "audio.write",     # 音频上传权限
        "image.read",      # 图片读取权限
        "image.write",     # 图片上传权限
        "ticket.read",     # 工单读取权限
        "ticket.create",   # 工单创建权限
    ),
    # 查看者只有只读权限
    "viewer": (
        "doc.read",        # 文档读取权限
        "audio.read",      # 音频读取权限
        "audio.search",    # 音频搜索权限
        "image.read",      # 图片读取权限
        "ticket.read",     # 工单读取权限
    ),
}