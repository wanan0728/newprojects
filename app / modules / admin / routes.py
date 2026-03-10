# 8.2
# app / modules / admin / routes.py
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ok
from app.core.api_schemas import ApiResponse
from app.core.errors import raise_err
from app.infra.db.deps import get_db
from app.modules.admin.schemas import (
    GrantRoleData,
    GrantRoleReq,
    GrantRow,
    ListGrantsResp,
    RevokeRoleData,
)
from app.modules.audit.hook import record
from app.modules.auth.models import Role, User, UserRoleGrant
from app.modules.authz.deps import permission_required
from app.modules.authz.scope_keys import scope_global

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _global_scope(_request) -> str:
    return scope_global()


AdminUser = permission_required("workspace.manage", scope_builder=_global_scope)


# 只有拥有workspace.manage（global）的用户，才能调用本admin模块


@router.post("/grants", response_model=ApiResponse[GrantRoleData], status_code=201)
async def grant_role(req: GrantRoleReq, me: User = Depends(AdminUser), db: AsyncSession = Depends(get_db)):
    # 给用户在某个scope下授予某个role

    role = (await db.execute(select(Role).where(Role.name == req.role_name))).scalar_one_or_none()
    # 先确认role是否存在，以role.name查

    if not role:
        record(
            action="admin.grant_role",
            status="deny",
            http_status=404,
            meta={
                "reason": "role_not_found",
                "role_name": str(req.role_name),
                "scope_key": str(req.scope_key),
                "target_user_id": int(req.user_id),
                "actor_user_id": int(me.id),
            },
            error_code="admin.role_not_found",
        )
        raise_err("admin.role_not_found")

    target = (await db.execute(select(User).where(User.id == req.user_id))).scalar_one_or_none()  # 再确认目标用户存在
    if not target:
        record(
            action="admin.grant_role",
            status="deny",
            http_status=404,
            meta={
                "reason": "user_not_found",
                "role_name": str(req.role_name),
                "scope_key": str(req.scope_key),
                "target_user_id": int(req.user_id),
                "actor_user_id": int(me.id),
            },
            error_code="admin.user_not_found",
        )
        raise_err("admin.user_not_found")

    exists = (  # 先查是否已经存在该授权，避免重复插入
        await db.execute(
            select(UserRoleGrant.id).where(
                UserRoleGrant.user_id == req.user_id,
                UserRoleGrant.role_id == role.id,
                UserRoleGrant.scope_key == req.scope_key,
            )
        )
    ).scalar_one_or_none()

    if exists:
        record(
            action="admin.grant_role",
            status="ok",
            meta={
                "idempotent": True,
                "role_name": str(req.role_name),
                "scope_key": str(req.scope_key),
                "target_user_id": int(req.user_id),
                "actor_user_id": int(me.id),
            },
        )
        return ok(GrantRoleData(granted=True, idempotent=True))

    try:
        stmt = (  # 用postgres的insert和on_conflict_do_nothing实现并发安全的最多插一条
            pg_insert(UserRoleGrant)
            .values(
                user_id=int(req.user_id),
                role_id=int(role.id),
                scope_key=str(req.scope_key),
                created_by=int(me.id),
            )
            .on_conflict_do_nothing(
                index_elements=[
                    UserRoleGrant.user_id,
                    UserRoleGrant.role_id,
                    UserRoleGrant.scope_key,
                ]
            )
        )

        async with db.begin():
            res = await db.execute(stmt)

        rc = int(getattr(res, "rowcount", 0) or 0)
        idempotent = (rc == 0)  # 如果rowcount=0也算幂等，比如说别人并发插入了，最终状态一致

        record(
            action="admin.grant_role",
            status="ok",
            meta={
                "idempotent": bool(idempotent),
                "role_name": str(req.role_name),
                "scope_key": str(req.scope_key),
                "target_user_id": int(req.user_id),
                "actor_user_id": int(me.id),
            },
        )

        return ok(GrantRoleData(granted=True, idempotent=idempotent))
    except Exception:
        logger.exception("grant_role unexpected error")
        record(
            action="admin.grant_role",
            status="error",
            http_status=500,
            meta={
                "role_name": str(req.role_name),
                "scope_key": str(req.scope_key),
                "target_user_id": int(req.user_id),
                "actor_user_id": int(me.id),
            },
            error_code="storage.db_error",
        )
        raise_err("storage.db_error")


@router.delete("/grants", response_model=ApiResponse[RevokeRoleData])
async def revoke_role(
        user_id: int = Query(...),
        role_name: str = Query(..., min_length=1, max_length=64),
        scope_key: str = Query(..., min_length=1, max_length=128),
        me: User = Depends(AdminUser),
        db: AsyncSession = Depends(get_db),
):
    role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if not role:
        record(
            action="admin.revoke_role",
            status="ok",
            meta={
                "idempotent": True,
                "role_name": str(role_name),
                "scope_key": str(scope_key),
                "target_user_id": int(user_id),
                "actor_user_id": int(me.id),
            },
        )
        return ok(RevokeRoleData(ok=True, deleted=0, idempotent=True))

    stmt = delete(UserRoleGrant).where(
        UserRoleGrant.user_id == int(user_id),
        UserRoleGrant.role_id == role.id,
        UserRoleGrant.scope_key == scope_key,
    )

    async with db.begin():
        res = await db.execute(stmt)

    deleted = int(res.rowcount or 0)

    record(
        action="admin.revoke_role",
        status="ok",
        meta={
            "deleted": int(deleted),
            "idempotent": (int(deleted) == 0),
            "role_name": str(role_name),
            "scope_key": str(scope_key),
            "target_user_id": int(user_id),
            "actor_user_id": int(me.id),
        },
    )

    return ok(RevokeRoleData(ok=True, deleted=deleted, idempotent=(deleted == 0)))


@router.get("/grants", response_model=ApiResponse[ListGrantsResp])
async def list_grants(
        user_id: int | None = Query(default=None),
        scope_key: str | None = Query(default=None),
        me: User = Depends(AdminUser),
        db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            UserRoleGrant.user_id,
            Role.name,
            UserRoleGrant.scope_key,
            UserRoleGrant.created_by,
            UserRoleGrant.created_at,
        )
        .join(Role, Role.id == UserRoleGrant.role_id)
    )

    if user_id is not None:
        stmt = stmt.where(UserRoleGrant.user_id == user_id)
    if scope_key is not None:
        stmt = stmt.where(UserRoleGrant.scope_key == scope_key)

    rows = (await db.execute(stmt)).all()

    items: list[GrantRow] = []
    for uid, role_name2, sk, created_by, created_at in rows:
        items.append(
            GrantRow(
                user_id=int(uid),
                role_name=str(role_name2),
                scope_key=str(sk),
                created_by=int(created_by) if created_by is not None else None,
                created_at=str(created_at),
            )
        )

    record(
        action="admin.list_grants",
        status="ok",
        meta={
            "user_id": int(user_id) if user_id is not None else None,
            "scope_key": str(scope_key) if scope_key is not None else None,
            "count": int(len(items)),
            "actor_user_id": int(me.id),
        },
    )

    return ok(ListGrantsResp(items=items))

