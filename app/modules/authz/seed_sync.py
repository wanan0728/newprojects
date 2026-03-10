# 7.4 app/modules/authz/seed_sync.py
# 权限种子数据同步模块
#
# 这个文件负责将 seed.py 中定义的预定义角色、权限以及默认角色-权限映射
# 同步到数据库中。它使用 PostgreSQL 的 ON CONFLICT 语法实现 upsert 操作，
# 确保数据存在且与代码定义保持一致，同时避免重复插入。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从sqlalchemy导入select函数，用于构建查询语句
from sqlalchemy import select
# 从sqlalchemy.dialects.postgresql导入insert并重命名为pg_insert
# 这是PostgreSQL特有的插入语句，支持ON CONFLICT子句（upsert）
from sqlalchemy.dialects.postgresql import insert as pg_insert
# 从sqlalchemy.ext.asyncio导入AsyncSession，用于异步数据库操作
from sqlalchemy.ext.asyncio import AsyncSession

# 从认证模块导入Permission、Role、RolePermission模型
# 这些模型对应数据库中的权限、角色和角色-权限关联表
from app.modules.auth.models import Permission, Role, RolePermission
# 从当前模块的seed导入预定义的常量：
#   DEFAULT_ROLE_PERMS: 默认角色拥有的权限代码字典
#   PERMISSIONS: 所有权限的元组（code, description）
#   ROLES: 所有角色的元组（name, description）
from app.modules.authz.seed import DEFAULT_ROLE_PERMS, PERMISSIONS, ROLES


# 定义异步函数sync_authz，用于将种子数据同步到数据库
# db: AsyncSession 参数，表示一个异步数据库会话
# -> None 表示该函数没有返回值
async def sync_authz(db: AsyncSession) -> None:
    """
    把seed.py中的roles/permissions同步进数据库，并补齐默认role-perm映射
    """
    # 开始一个数据库事务，async with db.begin() 确保事务自动提交或回滚
    async with db.begin():
        # 第一步：同步角色表
        # 遍历ROLES中的每个角色（name, description）
        for name, desc in ROLES:
            # 构建PostgreSQL的插入语句，使用pg_insert
            stmt = (
                pg_insert(Role)                              # 针对Role表的插入语句
                .values(name=str(name), description=str(desc))  # 设置要插入的值，确保为字符串类型
                .on_conflict_do_update(                       # 当发生唯一冲突时执行更新
                    index_elements=[Role.name],               # 冲突检测的索引列（Role.name唯一）
                    set_={"description": str(desc)},          # 冲突时更新description字段
                )
            )
            # 执行语句，await等待异步执行完成
            await db.execute(stmt)

        # 第二步：同步权限表
        # 遍历PERMISSIONS中的每个权限（code, description）
        for code, desc in PERMISSIONS:
            stmt = (
                pg_insert(Permission)                          # 针对Permission表的插入语句
                .values(code=str(code), description=str(desc)) # 设置值
                .on_conflict_do_update(                         # 冲突时更新
                    index_elements=[Permission.code],           # 冲突检测列（Permission.code唯一）
                    set_={"description": str(desc)},            # 更新description
                )
            )
            await db.execute(stmt)

        # 第三步：查询数据库中现有的所有角色和权限，用于后续建立关联
        # 执行select(Role)查询所有角色，.scalars().all() 获取所有Role对象列表
        role_rows = (await db.execute(select(Role))).scalars().all()
        # 执行select(Permission)查询所有权限，获取所有Permission对象列表
        perm_rows = (await db.execute(select(Permission))).scalars().all()

        # 构建角色名称到ID的映射字典，方便快速查找
        # 遍历role_rows，每个r是Role对象，用r.name作为键，r.id作为值
        role_map = {str(r.name): int(r.id) for r in role_rows}
        # 构建权限代码到ID的映射字典
        perm_map = {str(p.code): int(p.id) for p in perm_rows}

        # 查询数据库中已经存在的角色-权限关联关系，避免重复插入
        # select(RolePermission.role_id, RolePermission.perm_id) 获取所有关联的(role_id, perm_id)对
        # .all() 返回包含这些元组的列表，然后转换为set集合，用于快速判断是否存在
        existing = set((await db.execute(select(RolePermission.role_id, RolePermission.perm_id))).all())

        # 第四步：同步默认角色-权限映射
        # 遍历DEFAULT_ROLE_PERMS字典，role_name是角色名，perm_codes是该角色默认拥有的权限代码列表
        for role_name, perm_codes in DEFAULT_ROLE_PERMS.items():
            # 通过角色名从映射字典中获取角色ID
            rid = role_map.get(str(role_name))
            if rid is None:           # 如果角色ID不存在（理论上不应发生），跳过当前角色
                continue
            # 遍历该角色应该拥有的每个权限代码
            for code in perm_codes:
                # 通过权限代码获取权限ID
                pid = perm_map.get(str(code))
                if pid is None:       # 如果权限ID不存在，跳过该权限
                    continue
                # 检查(role_id, perm_id)是否已经存在于existing集合中
                if (rid, pid) in existing:
                    continue           # 如果已存在，跳过插入
                # 如果不存在，创建RolePermission关联对象并添加到数据库会话中
                db.add(RolePermission(role_id=int(rid), perm_id=int(pid)))
        # 事务结束时自动提交所有db.add的更改