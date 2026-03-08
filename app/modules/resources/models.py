# 5.5 app/modules/resources/models.py
# 资源管理模块数据库模型
#
# 这个文件定义了资源相关的数据库表结构，包括工作空间、项目、资源。
# 统一资源目录是把业务资源映射为可授权对象，我们这里是workspace/project/resource三层结构。
# 这样的设计可以实现细粒度的权限控制。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从datetime模块导入datetime类，用于定义日期时间类型的字段
from datetime import datetime

# 从sqlalchemy模块导入各种列类型和约束
from sqlalchemy import (
    BigInteger,  # 大整数类型，用于存储可能很大的ID
    DateTime,  # 日期时间类型，用于存储创建时间、更新时间
    ForeignKey,  # 外键约束，用于建立表之间的关联关系
    Index,  # 索引，用于加速查询
    String,  # 字符串类型，用于存储名称、描述等文本
    UniqueConstraint,  # 唯一约束，用于保证某些字段组合的唯一性
    text,  # 用于在SQL中嵌入原始文本，如条件索引中的WHERE子句
)

# 从sqlalchemy.orm导入Mapped和mapped_column
# Mapped: 类型注解，用于标记一个属性是映射到数据库列的
# mapped_column: 用于定义数据库列的函数，SQLAlchemy 2.0的新语法
from sqlalchemy.orm import Mapped, mapped_column

# 从sqlalchemy.sql导入func，提供SQL函数（如current_timestamp）
from sqlalchemy.sql import func

# 从数据库基类模块导入Base
# Base是所有数据库模型的基类，所有模型都需要继承它
from app.infra.db.base import Base


# 定义Workspace类，工作空间表
# 继承自Base，表示这是一个数据库模型
class Workspace(Base):
    """
    工作空间/组织容器表

    最顶层的资源隔离单位，相当于一个组织或团队。
    所有资源都归属于某个工作空间。
    """

    # __tablename__: 指定数据库中的表名
    __tablename__ = "workspaces"

    # __table_args__: 定义表的额外参数，包括约束和注释
    __table_args__ = (
        # UniqueConstraint: 唯一约束，保证工作空间名称唯一
        UniqueConstraint("name", name="uq_workspace_name"),
        # 表注释
        {"comment": "Workspace/Org container"},
    )

    # id: 工作空间ID，主键，自增
    # Mapped[int] 表示这是一个映射到整数类型的属性
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Workspace ID"  # 列注释
    )

    # name: 工作空间名称，唯一
    name: Mapped[str] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        nullable=False,  # 不能为空
        comment="Workspace name (unique)"  # 列注释
    )

    # description: 工作空间描述，可选
    description: Mapped[str | None] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=True,  # 可以为空
        comment="Workspace description"  # 列注释
    )

    # created_at: 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        comment="Created time"  # 列注释
    )

    # updated_at: 更新时间，自动更新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        onupdate=func.current_timestamp(),  # 更新时自动刷新为当前时间
        comment="Updated time",  # 列注释
    )


# 定义Project类，项目表
class Project(Base):
    """
    项目容器表，隶属于工作空间

    工作空间下的二级隔离单位，一个工作空间可以有多个项目。
    用于组织相关的资源，如文档、任务等。
    """

    # 指定表名
    __tablename__ = "projects"

    # 表额外参数：索引、约束和注释
    __table_args__ = (
        # 唯一约束：在同一工作空间下，项目名称必须唯一
        UniqueConstraint("workspace_id", "name", name="uq_ws_project_name"),
        # 索引：按工作空间查询项目，加速查询
        Index("idx_project_ws", "workspace_id"),
        # 表注释
        {"comment": "Project container under workspace"},
    )

    # id: 项目ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Project ID"  # 列注释
    )

    # workspace_id: 所属工作空间ID，外键
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("workspaces.id"),  # 外键关联到workspaces表的id字段
        nullable=False,  # 不能为空
        comment="FK -> workspaces.id"  # 列注释
    )

    # name: 项目名称，在工作空间内唯一
    name: Mapped[str] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        nullable=False,  # 不能为空
        comment="Project name (unique within workspace)"  # 列注释
    )

    # description: 项目描述，可选
    description: Mapped[str | None] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=True,  # 可以为空
        comment="Project description"  # 列注释
    )

    # created_at: 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        comment="Created time"  # 列注释
    )

    # updated_at: 更新时间，自动更新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        onupdate=func.current_timestamp(),  # 更新时自动刷新为当前时间
        comment="Updated time",  # 列注释
    )


# 定义Resource类，统一资源表
class Resource(Base):
    """
    统一资源目录，将业务资源映射为可授权对象

    我们这里是workspace/project/resource三层结构：
    - 工作空间（Workspace）：最顶层
    - 项目（Project）：工作空间下的分组
    - 资源（Resource）：具体的业务资源

    这样设计可以实现从工作空间级别到具体资源级别的权限控制。
    """

    # 指定表名
    __tablename__ = "resources"

    # 表额外参数：索引、约束和注释
    __table_args__ = (
        # 索引1：当project_id不为空时，在工作空间、项目、资源类型、业务ID的组合必须唯一
        # 这是一个条件唯一索引，只对project_id不为空的记录生效
        Index(
            "uq_resource_ws_proj_type_ref",  # 索引名称
            "workspace_id",  # 字段1：工作空间ID
            "project_id",  # 字段2：项目ID
            "resource_type",  # 字段3：资源类型
            "ref_id",  # 字段4：业务ID
            unique=True,  # 唯一索引
            postgresql_where=text("project_id IS NOT NULL"),  # PostgreSQL条件：只对project_id不为空的记录生效
        ),

        # 索引2：当project_id为空时，在工作空间、资源类型、业务ID的组合必须唯一
        # 这是一个条件唯一索引，只对project_id为空的记录生效
        Index(
            "uq_resource_ws_type_ref_no_proj",  # 索引名称
            "workspace_id",  # 字段1：工作空间ID
            "resource_type",  # 字段2：资源类型
            "ref_id",  # 字段3：业务ID
            unique=True,  # 唯一索引
            postgresql_where=text("project_id IS NULL"),  # PostgreSQL条件：只对project_id为空的记录生效
        ),

        # 索引3：按资源类型和业务ID查询，加速按资源类型和业务ID的查找
        Index("idx_type_ref", "resource_type", "ref_id"),

        # 表注释
        {"comment": "Unified resource directory for authorization"},
    )

    # id: 资源记录ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Resource row ID (internal)"  # 列注释
    )

    # workspace_id: 所属工作空间ID，外键
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("workspaces.id"),  # 外键关联到workspaces表的id字段
        nullable=False,  # 不能为空
        comment="Owning workspace id"  # 列注释
    )

    # project_id: 所属项目ID，可空（资源可以直接属于工作空间）
    project_id: Mapped[int | None] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("projects.id"),  # 外键关联到projects表的id字段
        nullable=True,  # 可以为空
        comment="Owning project id (nullable)"  # 列注释
    )

    # resource_type: 资源类型，可扩展
    resource_type: Mapped[str] = mapped_column(
        String(32),  # 列类型：长度32的字符串
        nullable=False,  # 不能为空
        comment="doc/audio/image/ticket/... (extensible)"
        # 示例值：doc（文档）、audio（音频）、image（图片）、ticket（工单）等
    )

    # ref_id: 业务表主键，指向具体业务数据的ID
    ref_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        nullable=False,  # 不能为空
        comment="Business table PK this resource refers to"
        # 例如：如果resource_type="doc"，ref_id就是documents表的ID
    )

    # created_by: 创建者用户ID，外键
    created_by: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("users.id"),  # 外键关联到users表的id字段
        nullable=False,  # 不能为空
        comment="Creator user_id"  # 列注释
    )

    # created_at: 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        comment="Created time"  # 列注释
    )

    # updated_at: 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认值：当前时间戳
        onupdate=func.current_timestamp(),  # 更新时自动刷新为当前时间
        comment="Updated time",  # 列注释
    )