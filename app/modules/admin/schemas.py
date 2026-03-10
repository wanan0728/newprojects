# 8.1 app/modules/admin/schemas.py
# 管理员模块数据模型定义
#
# 这个文件定义了管理员相关 API 的请求和响应数据模型。
# 主要用于角色授予、撤销和查询操作的参数校验与结果格式化。
# 管理员模块通常用于管理用户权限、查看授权信息等。

# 从__future__导入annotations功能，让类型注解在运行时不会被评估
from __future__ import annotations

# 从pydantic导入BaseModel和Field，用于定义数据模型和字段验证规则
from pydantic import BaseModel, Field


# 定义GrantRoleReq类，授予角色请求模型
class GrantRoleReq(BaseModel):  # 对user_id这个用户在scope_key资源下授予role_name权限
    """
    授予角色请求体

    属性:
        user_id: 目标用户ID
        role_name: 要授予的角色名称，长度1-64
        scope_key: 作用域键，标识授权生效的范围，长度1-128
    """
    user_id: int  # 目标用户ID，即要授予角色的用户
    role_name: str = Field(min_length=1, max_length=64)  # 角色名称，使用Field限制长度，必须1-64字符
    scope_key: str = Field(min_length=1, max_length=128)  # 作用域键，标识授权生效的范围（如"workspace:2"），长度1-128


# 定义GrantRoleData类，授予角色响应数据模型
class GrantRoleData(BaseModel):
    """
    授予角色响应数据

    属性:
        granted: 是否授予成功，默认True
        idempotent: 是否幂等命中，即本次操作前该授权已经存在
    """
    granted: bool = True  # 是否授予成功，默认True表示成功
    idempotent: bool  # 是否幂等命中，即本来就有这条grant，True表示之前已存在，未重复插入


# 定义RevokeRoleData类，撤销角色响应数据模型
class RevokeRoleData(BaseModel):
    """
    撤销角色响应数据

    属性:
        ok: 是否撤销成功，语义化字段，默认True
        deleted: 实际删除了几条记录
        idempotent: 是否幂等命中，即本来就没有该授权
    """
    ok: bool = True  # 是否撤销成功，语义化字段，默认True
    deleted: int  # 实际删除了几条记录，通常为0或1
    idempotent: bool  # 是否幂等命中，即本来就没有，True表示未做任何删除


# 定义GrantRow类，授权记录行模型
class GrantRow(BaseModel):
    """
    授权记录行，用于列表展示

    属性:
        user_id: 目标用户ID
        role_name: 角色名称
        scope_key: 作用域键
        created_by: 授权人用户ID（可能是管理员），可为空
        created_at: 授权时间，字符串格式
    """
    user_id: int  # 目标用户id
    role_name: str  # 角色名
    scope_key: str
    created_by: int | None  # 授权人用户ID，可能为None表示系统自动或未知
    created_at: str  # 授权时间，通常为ISO格式字符串


# 定义ListGrantsResp类，授权列表响应模型
class ListGrantsResp(BaseModel):
    """
    授权列表响应

    属性:
        items: 授权记录列表
    """
    # 为了给上一个添加一个items做前缀
    items: list[GrantRow]  # 授权记录列表，每个元素为GrantRow类型