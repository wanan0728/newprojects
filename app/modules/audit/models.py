# 3.2 app/modules/audit/models.py
# 审计日志数据库模型模块
#
# 这个文件定义了审计日志的数据库模型（表结构）。
# 审计日志用于记录所有关键操作，包括谁、什么时间、做了什么操作、
# 操作了哪个资源、结果如何等，便于后续审计和问题追踪。
# 每个字段都添加了注释，说明其用途。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从datetime模块导入datetime类
# 用于处理日期时间类型，如记录的创建时间
from datetime import datetime

# 从typing模块导入Any类型
# Any表示任意类型，用于meta字段，因为元数据可以是任意结构
from typing import Any

# 从sqlalchemy导入各种列类型和索引工具
# BigInteger: 大整数类型，适合存储可能很大的ID
# DateTime: 日期时间类型
# Index: 用于定义数据库索引
# Integer: 整数类型
# String: 字符串类型
# Text: 长文本类型
from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text

# 从sqlalchemy.orm导入Mapped和mapped_column
# Mapped: 类型注解，标记一个映射属性
# mapped_column: 定义数据库列的函数，SQLAlchemy 2.0的新语法
from sqlalchemy.orm import Mapped, mapped_column

# 从sqlalchemy.sql导入func
# func提供了SQL函数，如current_timestamp()获取当前时间
from sqlalchemy.sql import func

# 从sqlalchemy.types导入JSON
# JSON类型，用于存储任意JSON数据
from sqlalchemy.types import JSON

# 从数据库基类模块导入Base
# Base是所有数据库模型的基类，继承它才能被SQLAlchemy识别为模型
from app.infra.db.base import Base


# 定义AuditEvent类，继承自Base，对应数据库中的audit_events表
class AuditEvent(Base):
    # __tablename__: 指定数据库中的表名
    __tablename__ = "audit_events"

    # __table_args__: 定义表的额外参数，包括索引和注释
    __table_args__ = (
        # 在request_id字段上创建索引，加速按请求ID查询
        Index("idx_audit_request_id", "request_id"),

        # 在actor_user_id和created_at上创建复合索引，加速按用户和时间查询
        Index("idx_audit_actor_time", "actor_user_id", "created_at"),

        # 在action和created_at上创建复合索引，加速按操作类型和时间查询
        Index("idx_audit_action_time", "action", "created_at"),

        # 在resource_type和resource_ref_id上创建复合索引，加速按资源查询
        Index("idx_audit_resource", "resource_type", "resource_ref_id"),

        # 在workspace_id和created_at上创建复合索引，加速按租户和时间查询
        Index("idx_audit_ws_time", "workspace_id", "created_at"),

        # 表的注释
        {"comment": "Audit trail events"},
    )

    # id: 审计事件ID，主键
    # Mapped[int] 表示这是一个映射到整数类型的属性
    # mapped_column 定义列属性
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Audit event ID"  # 列注释
    )

    # request_id: 关联的请求ID
    # Mapped[str | None] 表示可以是字符串或None
    request_id: Mapped[str | None] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        nullable=True,  # 允许为空
        comment="Correlation request id"  # 关联的请求ID，用于追踪链路
    )

    # workspace_id: 租户工作空间ID
    # Mapped[int | None] 表示可以是整数或None
    workspace_id: Mapped[int | None] = mapped_column(
        BigInteger,  # 列类型：大整数
        nullable=True,  # 允许为空（系统级端点可能没有租户）
        comment="Tenant workspace_id (nullable for system endpoints)"  # 租户工作空间ID
    )

    # actor_user_id: 操作用户ID
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger,  # 列类型：大整数
        nullable=True,  # 允许为空（系统操作可能没有用户）
        comment="Actor user_id"  # 操作者用户ID
    )

    # action: 操作名称
    # Mapped[str] 表示必须是字符串
    action: Mapped[str] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        nullable=False,  # 不能为空
        comment="Action name"  # 操作名称，如 "create_user", "delete_document"
    )

    # scope_key: 作用域键
    scope_key: Mapped[str | None] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        nullable=True,  # 允许为空
        comment="Scope key"  # 作用域键，用于区分不同功能模块
    )

    # resource_type: 资源类型
    resource_type: Mapped[str | None] = mapped_column(
        String(32),  # 列类型：长度32的字符串
        nullable=True,  # 允许为空
        comment="Resource type"  # 资源类型，如 "user", "document"
    )

    # resource_ref_id: 资源引用ID
    resource_ref_id: Mapped[int | None] = mapped_column(
        BigInteger,  # 列类型：大整数
        nullable=True,  # 允许为空
        comment="Resource ref id"  # 资源ID，如用户ID、文档ID
    )

    # status: 操作状态
    status: Mapped[str] = mapped_column(
        String(16),  # 列类型：长度16的字符串
        nullable=False,  # 不能为空
        comment="ok/deny/error"  # 状态：成功/拒绝/错误
    )

    # http_status: HTTP状态码
    http_status: Mapped[int | None] = mapped_column(
        Integer,  # 列类型：整数
        nullable=True,  # 允许为空
        comment="HTTP status"  # HTTP状态码，如200、403、500
    )

    # ip: 客户端IP地址
    ip: Mapped[str | None] = mapped_column(
        String(64),  # 列类型：长度64的字符串
        nullable=True,  # 允许为空
        comment="Client IP"  # 客户端IP
    )

    # user_agent: 客户端User-Agent
    user_agent: Mapped[str | None] = mapped_column(
        Text,  # 列类型：长文本
        nullable=True,  # 允许为空
        comment="User-Agent"  # 客户端浏览器/设备信息
    )

    # meta: 额外的元数据（JSON格式）
    # Mapped[dict[str, Any] | None] 表示可以是字典或None
    meta: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,  # 列类型：JSON
        nullable=True,  # 允许为空
        comment="Extra metadata (json)"  # 额外的元数据，以JSON格式存储
    )

    # created_at: 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        comment="Created time"  # 创建时间
    )