# 8.2 app/modules/admin/routes.py
# 管理员模块路由定义
#
# 这个文件定义了管理员相关的API路由，包括角色授予、撤销和查询。
# 管理员模块用于管理用户权限，通常只有具备 workspace.manage 全局权限的用户才能访问。

# 从__future__导入annotations功能，让类型注解在运行时不会被评估
from __future__ import annotations

# 导入logging模块，用于记录异常日志
import logging

# 从fastapi导入APIRouter、Depends、Query，用于创建路由、依赖注入和查询参数解析
from fastapi import APIRouter, Depends, Query
# 从sqlalchemy导入delete和select，用于构建删除和查询语句
from sqlalchemy import delete, select
# 从sqlalchemy.dialects.postgresql导入insert并重命名为pg_insert，用于PostgreSQL的upsert操作
from sqlalchemy.dialects.postgresql import insert as pg_insert
# 从sqlalchemy.ext.asyncio导入AsyncSession，用于异步数据库操作
from sqlalchemy.ext.asyncio import AsyncSession

# 从核心响应模块导入ok，用于包装成功响应
from app.core.api_response import ok
# 从核心API模式模块导入ApiResponse，用于响应类型注解
from app.core.api_schemas import ApiResponse
# 从错误处理模块导入raise_err，用于抛出异常
from app.core.errors import raise_err
# 从数据库依赖模块导入get_db，用于获取数据库会话
from app.infra.db.deps import get_db
# 从当前模块的schemas导入所有管理员模式
from app.modules.admin.schemas import (
    GrantRoleData,    # 授予角色响应数据
    GrantRoleReq,     # 授予角色请求体
    GrantRow,         # 授权记录行模型
    ListGrantsResp,   # 授权列表响应
    RevokeRoleData,   # 撤销角色响应数据
)
# 从审计钩子模块导入record，用于记录审计日志
from app.modules.audit.hook import record
# 从认证模块导入Role、User、UserRoleGrant模型
from app.modules.auth.models import Role, User, UserRoleGrant
# 从权限依赖模块导入permission_required，用于创建权限检查依赖
from app.modules.authz.deps import permission_required
# 从权限作用域工具模块导入scope_global，用于生成全局作用域键
from app.modules.authz.scope_keys import scope_global

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

# 创建APIRouter实例，所有管理员路由都加上/admin前缀
router = APIRouter(prefix="/admin", tags=["admin"])


# 定义一个辅助函数，始终返回全局作用域，用于权限依赖的scope_builder
def _global_scope(_request) -> str:
    return scope_global()  # 返回 "global" 字符串


# 创建管理员权限依赖：只有拥有 workspace.manage 全局权限的用户才能调用本admin模块
# permission_required 接收权限码和作用域构建器，返回一个依赖函数
AdminUser = permission_required("workspace.manage", scope_builder=_global_scope)


# 只有拥有workspace.manage（global）的用户，才能调用本admin模块


# 定义授予角色的路由：POST /admin/grants
@router.post("/grants", response_model=ApiResponse[GrantRoleData], status_code=201)
async def grant_role(req: GrantRoleReq, me: User = Depends(AdminUser), db: AsyncSession = Depends(get_db)):
    # 给用户在某个scope下授予某个role

    # 查询角色是否存在，通过角色名称查找
    role = (await db.execute(select(Role).where(Role.name == req.role_name))).scalar_one_or_none()
    # 先确认role是否存在，以role.name查

    # 如果角色不存在
    if not role:
        # 记录审计日志：角色不存在
        record(
            action="admin.grant_role",  # 操作名称：授予角色
            status="deny",              # 状态：拒绝
            http_status=404,            # HTTP状态码：404 Not Found
            meta={                       # 元数据：包含操作的详细信息
                "reason": "role_not_found",               # 原因：角色未找到
                "role_name": str(req.role_name),          # 请求的角色名称
                "scope_key": str(req.scope_key),          # 请求的作用域键
                "target_user_id": int(req.user_id),       # 目标用户ID
                "actor_user_id": int(me.id),              # 执行操作的管理员用户ID
            },
            error_code="admin.role_not_found",  # 错误码：角色未找到
        )
        raise_err("admin.role_not_found")  # 抛出角色不存在异常

    # 查询目标用户是否存在
    target = (await db.execute(select(User).where(User.id == req.user_id))).scalar_one_or_none()  # 再确认目标用户存在
    if not target:  # 如果目标用户不存在
        record(
            action="admin.grant_role",  # 操作名称：授予角色
            status="deny",              # 状态：拒绝
            http_status=404,            # HTTP状态码：404 Not Found
            meta={                       # 元数据
                "reason": "user_not_found",               # 原因：用户未找到
                "role_name": str(req.role_name),          # 请求的角色名称
                "scope_key": str(req.scope_key),          # 请求的作用域键
                "target_user_id": int(req.user_id),       # 目标用户ID
                "actor_user_id": int(me.id),              # 执行操作的管理员用户ID
            },
            error_code="admin.user_not_found",  # 错误码：用户未找到
        )
        raise_err("admin.user_not_found")  # 抛出用户不存在异常

    # 先查询是否已经存在该授权，避免重复插入
    exists = (  # 先查是否已经存在该授权，避免重复插入
        await db.execute(
            select(UserRoleGrant.id).where(
                UserRoleGrant.user_id == req.user_id,   # 条件：用户ID匹配
                UserRoleGrant.role_id == role.id,       # 条件：角色ID匹配
                UserRoleGrant.scope_key == req.scope_key,  # 条件：作用域键匹配
            )
        )
    ).scalar_one_or_none()

    # 如果授权已存在
    if exists:
        record(
            action="admin.grant_role",  # 操作名称：授予角色
            status="ok",                # 状态：成功
            meta={                       # 元数据
                "idempotent": True,                        # 幂等：True，表示已存在未重复插入
                "role_name": str(req.role_name),          # 角色名称
                "scope_key": str(req.scope_key),          # 作用域键
                "target_user_id": int(req.user_id),       # 目标用户ID
                "actor_user_id": int(me.id),              # 操作者ID
            },
        )
        return ok(GrantRoleData(granted=True, idempotent=True))  # 返回幂等成功响应

    try:
        # 构建PostgreSQL插入语句，使用on_conflict_do_nothing实现并发安全的最多插一条
        stmt = (  # 用postgres的insert和on_conflict_do_nothing实现并发安全的最多插一条
            pg_insert(UserRoleGrant)  # 针对UserRoleGrant表的插入语句
            .values(
                user_id=int(req.user_id),          # 用户ID
                role_id=int(role.id),              # 角色ID
                scope_key=str(req.scope_key),      # 作用域键
                created_by=int(me.id),             # 创建者（当前管理员ID）
            )
            .on_conflict_do_nothing(
                index_elements=[
                    UserRoleGrant.user_id,          # 冲突检测列：user_id
                    UserRoleGrant.role_id,          # 冲突检测列：role_id
                    UserRoleGrant.scope_key,        # 冲突检测列：scope_key
                ]
            )
        )

        # 在事务中执行插入语句
        async with db.begin():
            res = await db.execute(stmt)  # 执行语句

        # 获取影响的行数（rowcount），如果为0表示未插入（幂等）
        rc = int(getattr(res, "rowcount", 0) or 0)  # 获取rowcount，若不存在则默认0
        idempotent = (rc == 0)  # 如果rowcount=0也算幂等，比如说别人并发插入了，最终状态一致

        # 记录授予成功的审计日志
        record(
            action="admin.grant_role",  # 操作名称：授予角色
            status="ok",                # 状态：成功
            meta={                       # 元数据
                "idempotent": bool(idempotent),            # 是否幂等
                "role_name": str(req.role_name),          # 角色名称
                "scope_key": str(req.scope_key),          # 作用域键
                "target_user_id": int(req.user_id),       # 目标用户ID
                "actor_user_id": int(me.id),              # 操作者ID
            },
        )

        # 返回成功响应
        return ok(GrantRoleData(granted=True, idempotent=idempotent))
    except Exception:  # 捕获任何异常
        logger.exception("grant_role unexpected error")  # 记录异常日志
        record(
            action="admin.grant_role",  # 操作名称：授予角色
            status="error",             # 状态：错误
            http_status=500,            # HTTP状态码：500 Internal Server Error
            meta={                       # 元数据
                "role_name": str(req.role_name),          # 角色名称
                "scope_key": str(req.scope_key),          # 作用域键
                "target_user_id": int(req.user_id),       # 目标用户ID
                "actor_user_id": int(me.id),              # 操作者ID
            },
            error_code="storage.db_error",  # 错误码：数据库错误
        )
        raise_err("storage.db_error")  # 抛出数据库错误异常


# 定义撤销角色的路由：DELETE /admin/grants
@router.delete("/grants", response_model=ApiResponse[RevokeRoleData])
async def revoke_role(
        user_id: int = Query(...),  # 必需查询参数：目标用户ID，从URL查询字符串中获取
        role_name: str = Query(..., min_length=1, max_length=64),  # 必需查询参数：角色名称，长度限制1-64字符
        scope_key: str = Query(..., min_length=1, max_length=128),  # 必需查询参数：作用域键，长度限制1-128字符
        me: User = Depends(AdminUser),  # 通过依赖获取当前管理员用户（已通过权限检查）
        db: AsyncSession = Depends(get_db),  # 通过依赖获取数据库会话
):
    # 查询角色是否存在，通过角色名称从数据库中查找
    role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if not role:  # 如果角色不存在（查询结果为None）
        # 记录审计日志：角色不存在，但操作仍算成功（幂等），因为删除0条记录
        record(
            action="admin.revoke_role",  # 操作名称：撤销角色
            status="ok",                  # 状态：成功（即使角色不存在，也算成功，因为目标状态已达成）
            meta={                         # 元数据：包含操作的详细信息
                "idempotent": True,                        # 是否幂等命中：True，因为角色不存在，未做任何删除
                "role_name": str(role_name),               # 请求的角色名称
                "scope_key": str(scope_key),               # 请求的作用域键
                "target_user_id": int(user_id),            # 目标用户ID
                "actor_user_id": int(me.id),               # 执行操作的管理员用户ID
            },
        )
        # 返回成功响应，deleted=0，idempotent=True，表示未删除任何记录
        return ok(RevokeRoleData(ok=True, deleted=0, idempotent=True))

    # 构建删除语句，删除符合条件的授权记录
    stmt = delete(UserRoleGrant).where(
        UserRoleGrant.user_id == int(user_id),   # 条件：用户ID匹配
        UserRoleGrant.role_id == role.id,       # 条件：角色ID匹配
        UserRoleGrant.scope_key == scope_key,   # 条件：作用域键匹配
    )

    # 在事务中执行删除
    async with db.begin():
        res = await db.execute(stmt)  # 执行删除语句

    # 获取实际删除的行数
    deleted = int(res.rowcount or 0)  # 获取影响行数，若为None则转为0

    # 记录撤销操作的审计日志
    record(
        action="admin.revoke_role",  # 操作名称：撤销角色
        status="ok",                 # 状态：成功
        meta={                        # 元数据
            "deleted": int(deleted),                     # 实际删除的记录数
            "idempotent": (int(deleted) == 0),           # 是否幂等（删除0条表示原本就不存在）
            "role_name": str(role_name),                  # 角色名称
            "scope_key": str(scope_key),                  # 作用域键
            "target_user_id": int(user_id),               # 目标用户ID
            "actor_user_id": int(me.id),                  # 执行操作的管理员用户ID
        },
    )

    # 返回成功响应，包含删除数量和幂等标识
    return ok(RevokeRoleData(ok=True, deleted=deleted, idempotent=(deleted == 0)))


# 定义查询授权列表的路由：GET /admin/grants
@router.get("/grants", response_model=ApiResponse[ListGrantsResp])
async def list_grants(
        user_id: int | None = Query(default=None),   # 可选查询参数：按用户ID过滤，默认None
        scope_key: str | None = Query(default=None), # 可选查询参数：按作用域键过滤，默认None
        me: User = Depends(AdminUser),                # 通过依赖获取当前管理员用户（已通过权限检查）
        db: AsyncSession = Depends(get_db),           # 通过依赖获取数据库会话
):
    # 构建查询语句：从UserRoleGrant表关联Role表，选择需要的字段
    stmt = (
        select(
            UserRoleGrant.user_id,          # 用户ID
            Role.name,                      # 角色名称
            UserRoleGrant.scope_key,        # 作用域键
            UserRoleGrant.created_by,       # 创建者ID（授权人）
            UserRoleGrant.created_at,       # 创建时间
        )
        .join(Role, Role.id == UserRoleGrant.role_id)  # 内连接Role表
    )

    # 如果传入了user_id，添加过滤条件
    if user_id is not None:
        stmt = stmt.where(UserRoleGrant.user_id == user_id)  # 按用户ID过滤
    # 如果传入了scope_key，添加过滤条件
    if scope_key is not None:
        stmt = stmt.where(UserRoleGrant.scope_key == scope_key)  # 按作用域键过滤

    # 执行查询，获取所有结果
    rows = (await db.execute(stmt)).all()  # 返回所有行

    # 将查询结果转换为GrantRow对象列表
    items: list[GrantRow] = []
    for uid, role_name2, sk, created_by, created_at in rows:
        items.append(
            GrantRow(
                user_id=int(uid),                                # 用户ID
                role_name=str(role_name2),                      # 角色名称
                scope_key=str(sk),                               # 作用域键
                created_by=int(created_by) if created_by is not None else None,  # 创建者ID，可能为空
                created_at=str(created_at),                     # 创建时间（转为字符串）
            )
        )

    # 记录查询操作的审计日志
    record(
        action="admin.list_grants",  # 操作名称：列出授权
        status="ok",                 # 状态：成功
        meta={                        # 元数据
            "user_id": int(user_id) if user_id is not None else None,  # 查询的用户ID（可能None）
            "scope_key": str(scope_key) if scope_key is not None else None,  # 查询的作用域键（可能None）
            "count": int(len(items)),                          # 返回的记录数量
            "actor_user_id": int(me.id),                       # 执行操作的管理员用户ID
        },
    )

    # 返回成功响应，包含授权列表
    return ok(ListGrantsResp(items=items))