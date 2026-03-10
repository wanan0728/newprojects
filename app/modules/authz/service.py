# 7.5 app/modules/authz/service.py
# 权限检查服务模块
#
# 这个文件提供了核心的权限检查功能，用于判断用户是否拥有执行某个操作所需的权限。
# 主要函数 require_perms 会根据用户、作用域和所需权限列表进行验证，
# 如果没有权限则抛出异常并记录审计日志。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从sqlalchemy导入select函数，用于构建查询语句
from sqlalchemy import select
# 从sqlalchemy.ext.asyncio导入AsyncSession，用于异步数据库操作
from sqlalchemy.ext.asyncio import AsyncSession

# 从错误处理模块导入抛出异常的函数
from app.core.errors import raise_err
# 从审计钩子模块导入记录审计事件的函数
from app.modules.audit.hook import record
# 从认证模块导入相关的数据库模型
from app.modules.auth.models import Permission, RolePermission, User, UserRoleGrant
# 从权限作用域工具模块导入scopes_with_global函数
from app.modules.authz.scope_keys import scopes_with_global


# 定义异步函数require_perms，这是权限检查的核心函数
# 没有权限就抛错，并记录审计
async def require_perms(
    db: AsyncSession,          # 数据库会话对象，用于执行异步查询
    *,                          # 星号表示后面的参数必须用关键字传递
    user: User,                 # 当前用户对象，包含用户信息（如id, is_superadmin等）
    scope_key: str,             # 当前请求的作用域键，例如 "workspace:2" 或 "global"
    perm_codes: list[str],      # 需要检查的权限代码列表，例如 ["doc.read", "doc.write"]
) -> None:                      # 函数没有返回值，如果没有权限则抛出异常
    # 第一步：检查用户是否为超级管理员
    # 如果用户是超级管理员（is_superadmin 字段值为 True），则跳过所有权限检查
    if int(user.is_superadmin) == 1:   # 将布尔值转为整数，确保准确比较
        return                           # 直接返回，放行该请求

    # 第二步：检查是否需要权限验证
    # 如果 perm_codes 为空列表，说明没有要求任何权限，直接通过
    if not perm_codes:                  # 没有要求权限则直接通过
        return                           # 直接返回，放行

    # 第三步：生成包含全局作用域的作用域列表
    # scopes_with_global(scope_key) 函数根据传入的 scope_key 返回一个列表
    # 例如：如果 scope_key="workspace:2"，返回 ["workspace:2", "global"]
    # 如果 scope_key="global"，返回 ["global"]
    scopes = scopes_with_global(scope_key)  # 计算当前scope + global，让全局授权也能生效

    # 第四步：查询用户在给定作用域下拥有的所有角色ID
    # 构建查询：从 UserRoleGrant 表中选择 role_id 字段
    role_ids_query = select(UserRoleGrant.role_id).where(
        UserRoleGrant.user_id == user.id,          # 用户ID匹配
        UserRoleGrant.scope_key.in_(scopes),       # 作用域在 scopes 列表中
    )
    # 执行查询，使用 scalars().all() 获取所有查询结果作为一个列表（每个元素是 role_id）
    role_ids = (await db.execute(role_ids_query)).scalars().all()  # 查用户在这些scopes下有哪些role_id

    # 第五步：如果没有查询到任何角色ID，说明用户在该作用域下没有被授予任何角色
    if not role_ids:                               # 用户在该scope下没有任何role
        # 记录审计日志：缺少角色
        record(
            action="rbac.role_required",           # 操作名称：需要角色
            status="deny",                          # 状态：拒绝
            http_status=403,                        # HTTP状态码：403 Forbidden
            meta={"scope_key": str(scope_key), "user_id": int(user.id)},  # 附加元数据：作用域和用户ID
            error_code="rbac.role_required",        # 错误码：缺少角色
        )
        # 抛出权限异常，提示缺少角色，同时携带元数据便于前端处理
        raise_err("rbac.role_required", meta={"scope_key": scope_key})

    # 第六步：查询这些角色所拥有的权限中，是否包含所需权限
    # 构建查询：从 Permission 表中选择 code 字段
    perm_query = (
        select(Permission.code)                     # 选择权限代码
        .join(RolePermission, RolePermission.perm_id == Permission.id)  # 关联角色-权限表
        .where(
            RolePermission.role_id.in_(role_ids),   # 角色ID在用户拥有的角色列表内
            Permission.code.in_(perm_codes),        # 权限代码在需要检查的列表内
        )
    )
    # 执行查询，获得所有匹配的权限代码
    rows = (await db.execute(perm_query)).scalars().all()  # 再查这些roles命中的权限code

    # 第七步：计算缺失的权限
    have = {str(x) for x in rows}                   # 将查询到的权限代码转换为集合，便于差集计算
    # 遍历所需权限列表，找出不在 have 集合中的权限，保持原顺序便于调试
    missing = [p for p in perm_codes if p not in have]  # 计算缺失的权限列表，保持原顺序便于调试

    # 第八步：如果存在缺失的权限
    if missing:                                     # 如果有缺失的权限
        # 记录审计日志：缺少权限
        record(
            action="rbac.permission_missing",       # 操作名称：缺少权限
            status="deny",                          # 状态：拒绝
            http_status=403,                        # HTTP状态码：403 Forbidden
            meta={                                   # 附加元数据
                "scope_key": str(scope_key),        # 当前作用域
                "missing": list(missing),           # 缺失的权限列表
                "user_id": int(user.id),            # 用户ID
            },
            error_code="rbac.permission_missing",   # 错误码：缺少权限
        )
        # 抛出权限异常，提示缺少哪些权限
        raise_err("rbac.permission_missing", meta={"scope_key": scope_key, "missing": missing})