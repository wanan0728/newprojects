# 5.4 app/modules/auth/models.py
# 认证授权模块数据库模型
#
# 这个文件定义了用户认证和授权相关的所有数据库表结构。
# 包括用户表、角色表、权限表，以及它们之间的关联关系。
# 实现了基于RBAC（基于角色的访问控制）的权限模型。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从datetime导入datetime类，用于处理日期时间类型
from datetime import datetime

# 从sqlalchemy导入各种列类型和约束
from sqlalchemy import (
    BigInteger,  # 大整数类型，用于存储可能很大的ID
    Boolean,  # 布尔类型，用于存储真/假值
    DateTime,  # 日期时间类型，用于存储创建时间、更新时间
    ForeignKey,  # 外键约束，用于建立表之间的关联关系
    Index,  # 索引，用于加速查询
    String,  # 字符串类型，用于存储名称、邮箱等文本
    UniqueConstraint,  # 唯一约束，用于保证某些字段组合的唯一性
    text,  # 用于原始SQL文本，如server_default中的"true"、"false"
)
# 从sqlalchemy.orm导入Mapped和mapped_column
# Mapped: 类型注解，标记一个映射属性
# mapped_column: 定义数据库列的函数，SQLAlchemy 2.0的新语法
from sqlalchemy.orm import Mapped, mapped_column

# 从sqlalchemy.sql导入func，提供SQL函数（如current_timestamp）
from sqlalchemy.sql import func

# 从数据库基类模块导入Base
# Base是所有数据库模型的基类，所有模型都需要继承它
from app.infra.db.base import Base


# 定义User类，用户表
class User(Base):
    """系统用户表 - 存储所有用户的基本信息"""

    # __tablename__: 指定数据库中的表名
    __tablename__ = "users"

    # __table_args__: 定义表的额外参数
    __table_args__ = {"comment": "System users"}  # 表注释

    # id: 用户ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="User ID (internal PK)"  # 列注释：用户ID（内部主键）
    )

    # email: 用户邮箱，用于登录，唯一
    email: Mapped[str] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        unique=True,  # 唯一约束
        nullable=False,  # 不能为空
        comment="Login email (unique)"  # 登录邮箱（唯一）
    )

    # password_hash: 密码哈希值，使用argon2id算法
    password_hash: Mapped[str] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=False,  # 不能为空
        comment="Password hash (argon2id)"  # 密码哈希（argon2id算法）
    )

    # is_active: 用户是否激活，默认true
    is_active: Mapped[bool] = mapped_column(
        Boolean,  # 列类型：布尔
        nullable=False,  # 不能为空
        server_default=text("true"),  # 数据库默认值为true（使用text包装）
        comment="Active user"  # 激活用户
    )

    # is_superadmin: 是否为超级管理员，默认false
    # 超级管理员拥有所有权限，绕过所有权限检查
    is_superadmin: Mapped[bool] = mapped_column(
        Boolean,  # 列类型：布尔
        nullable=False,  # 不能为空
        server_default=text("false"),  # 数据库默认值为false
        comment="Bypass all authz"  # 绕过所有权限检查
    )

    # created_at: 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认当前时间
        comment="Created time"  # 创建时间
    )

    # updated_at: 更新时间，自动更新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认当前时间
        onupdate=func.current_timestamp(),  # 更新时自动刷新为当前时间
        comment="Updated time",  # 更新时间
    )


# 定义UserIdentity类，外部用户身份表
class UserIdentity(Base):
    """
    外部用户表，后来做其他SSO做个预留

    用于未来集成第三方认证（OIDC、SAML等），
    将外部身份映射到系统用户。
    """

    # 指定表名
    __tablename__ = "user_identities"

    # 表额外参数：约束、索引和注释
    __table_args__ = (
        # 联合唯一约束：同一个提供商下，subject必须唯一
        UniqueConstraint("provider", "subject", name="uq_provider_subject"),
        # 索引：按用户ID和提供商查询，加速查找
        Index("idx_user_provider", "user_id", "provider"),
        # 表注释
        {"comment": "External identities (future SSO/OIDC/SAML)"},
    )

    # id: 身份记录ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Identity row ID"  # 身份记录ID
    )

    # user_id: 关联的系统用户ID，外键
    user_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("users.id"),  # 外键关联到users表的id字段
        nullable=False,  # 不能为空
        comment="FK -> users.id"  # 外键：关联到users表
    )

    # provider: 身份提供商，如google、okta等
    provider: Mapped[str] = mapped_column(
        String(32),  # 列类型：长度32的字符串
        nullable=False,  # 不能为空
        comment="Provider: local/google/okta/... (future)"  # 身份提供商
    )

    # subject: 在提供商处的唯一标识
    subject: Mapped[str] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=False,  # 不能为空
        comment="Provider subject (OIDC sub / SAML NameID)"  # 提供商处的唯一标识
    )

    # email: 提供商处的邮箱（可选）
    email: Mapped[str | None] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=True,  # 可以为空
        comment="Provider email (optional)"  # 提供商处的邮箱（可选）
    )

    # created_at: 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认当前时间
        comment="Created time"  # 创建时间
    )


# 定义Role类，角色表
class Role(Base):
    """RBAC角色表 - 定义系统中的角色"""

    # 指定表名
    __tablename__ = "roles"

    # 表注释
    __table_args__ = {"comment": "RBAC roles"}

    # id: 角色ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Role ID"  # 角色ID
    )

    # name: 角色名称，唯一
    name: Mapped[str] = mapped_column(
        String(64),  # 列类型：长度64的字符串
        unique=True,  # 唯一约束
        nullable=False,  # 不能为空
        comment="Role name (unique)"  # 角色名称（唯一）
    )

    # description: 角色描述，可选
    description: Mapped[str | None] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=True,  # 可以为空
        comment="Role description"  # 角色描述
    )


# 定义Permission类，权限表
class Permission(Base):
    """
    权限注册表 - 定义系统中所有可用的权限

    code是稳定标识，一旦定义不应修改
    """

    # 指定表名
    __tablename__ = "permissions"

    # 表注释
    __table_args__ = {"comment": "Permission registry (code is stable identifier)"}

    # id: 权限ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Permission ID"  # 权限ID
    )

    # code: 权限代码，如 "doc.read", "user.create"，唯一
    code: Mapped[str] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        unique=True,  # 唯一约束
        nullable=False,  # 不能为空
        comment="Permission code like doc.read"  # 权限代码
    )

    # description: 权限描述，可选
    description: Mapped[str | None] = mapped_column(
        String(255),  # 列类型：长度255的字符串
        nullable=True,  # 可以为空
        comment="Permission description"  # 权限描述
    )


# 定义RolePermission类，角色-权限关联表
class RolePermission(Base):
    """角色和权限的多对多关系表"""

    # 指定表名
    __tablename__ = "role_permissions"

    # 表注释
    __table_args__ = {"comment": "Role -> Permission mapping"}

    # role_id: 角色ID，外键，联合主键的一部分
    role_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("roles.id"),  # 外键关联到roles表的id字段
        primary_key=True,  # 作为联合主键
        comment="FK -> roles.id"  # 外键：关联到roles表
    )

    # perm_id: 权限ID，外键，联合主键的一部分
    perm_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("permissions.id"),  # 外键关联到permissions表的id字段
        primary_key=True,  # 作为联合主键
        comment="FK -> permissions.id"  # 外键：关联到permissions表
    )


# 定义UserRoleGrant类，用户-角色授权表
class UserRoleGrant(Base):
    """
    用户角色授权表 - 将角色授予用户，并限定作用域

    支持不同作用域的授权，如全局、工作空间、项目、资源级别
    """

    # 指定表名
    __tablename__ = "user_role_grants"

    # 表额外参数：约束、索引和注释
    __table_args__ = (
        # 联合唯一约束：同一个用户在同一作用域下不能有重复角色
        UniqueConstraint("user_id", "role_id", "scope_key", name="uq_user_role_scope"),
        # 索引：按用户和作用域查询，加速查找
        Index("idx_user_scope", "user_id", "scope_key"),
        # 索引：按作用域查询，加速查找
        Index("idx_scope", "scope_key"),
        # 表注释
        {"comment": "User role grants scoped by scope_key"},
    )

    # id: 授权记录ID，主键，自增
    id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        primary_key=True,  # 主键
        autoincrement=True,  # 自增
        comment="Grant row ID"  # 授权记录ID
    )

    # user_id: 用户ID，外键
    user_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("users.id"),  # 外键关联到users表的id字段
        nullable=False,  # 不能为空
        comment="FK -> users.id"  # 外键：关联到users表
    )

    # role_id: 角色ID，外键
    role_id: Mapped[int] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("roles.id"),  # 外键关联到roles表的id字段
        nullable=False,  # 不能为空
        comment="FK -> roles.id"  # 外键：关联到roles表
    )

    # scope_key: 作用域键，定义授权生效的范围
    scope_key: Mapped[str] = mapped_column(
        String(128),  # 列类型：长度128的字符串
        nullable=False,  # 不能为空
        comment="global | workspace:{id} | project:{id} | resource:{type}:{ref_id}",
        # 示例值：
        #   "global"  - 全局生效
        #   "workspace:123" - 在某个工作空间生效
        #   "project:456"   - 在某个项目生效
        #   "resource:doc:789" - 在某个具体资源生效
    )

    # created_by: 授权人（哪个管理员授予的），外键
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,  # 列类型：大整数
        ForeignKey("users.id"),  # 外键关联到users表的id字段
        nullable=True,  # 可以为空
        comment="Granting admin user_id"  # 授权人用户ID
    )

    # created_at: 授权时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # 列类型：带时区的日期时间
        nullable=False,  # 不能为空
        server_default=func.current_timestamp(),  # 数据库默认当前时间
        comment="Grant time"  # 授权时间
    )