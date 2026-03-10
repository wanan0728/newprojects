# 8.1
# app / modules / admin / schemas.py
from __future__ import annotations

from pydantic import BaseModel, Field


class GrantRoleReq(BaseModel):  # 对user_id这个用户在scope_key资源下授予role_name权限
    user_id: int
    role_name: str = Field(min_length=1, max_length=64)
    scope_key: str = Field(min_length=1, max_length=128)


class GrantRoleData(BaseModel):
    granted: bool = True  # 是否授予成功
    idempotent: bool  # 是否幂等命中，即本来就有这条grant


class RevokeRoleData(BaseModel):
    ok: bool = True  # 是否撤销成功，语义化字段
    deleted: int  # 实际删除了几条
    idempotent: bool  # 是否幂等命中，即本来就没有


class GrantRow(BaseModel):
    user_id: int  # 目标用户id
    role_name: str  # 角色名
    scope_key: str
    created_by: int | None
    created_at: str


class ListGrantsResp(BaseModel):
    # 为了给上一个添加一个items做前缀
    items: list[GrantRow]


