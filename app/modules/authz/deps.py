# 7.6 app/modules/authz/deps.py
# 权限依赖模块
#
# 这个文件定义了用于权限检查的FastAPI依赖项。它提供了一个工厂函数 permission_required，
# 可以根据传入的权限码和作用域构建器生成一个依赖，用于在路径操作中检查用户是否拥有指定权限。

# 从__future__导入annotations功能，让类型注解在运行时不会被评估
from __future__ import annotations

# 从typing导入Callable，用于类型注解，表示可调用对象（函数）
from typing import Callable

# 从fastapi导入Depends（依赖注入）、Request（请求对象）
from fastapi import Depends, Request
# 从sqlalchemy.ext.asyncio导入AsyncSession，用于异步数据库会话
from sqlalchemy.ext.asyncio import AsyncSession

# 从数据库依赖模块导入get_db，用于获取数据库会话
from app.infra.db.deps import get_db
# 从认证模块导入User模型，用于类型注解
from app.modules.auth.models import User
# 从认证依赖模块导入get_current_user，用于获取当前登录用户
from app.modules.authn.deps import get_current_user
# 从权限服务模块导入require_perms，用于执行核心权限检查
from app.modules.authz.service import require_perms


# 定义permission_required函数，这是一个工厂函数，返回一个FastAPI依赖项
def permission_required(
        *perm_codes: str,  # *表示可变参数，即这里有0个或多个权限码，例如 "doc.read", "doc.write"
        scope_builder: Callable[[Request], str]):  # 此处要接受一个函数，该函数接收Request并返回作用域字符串（如 "workspace:2"）
    """
    创建一个权限检查依赖项

    参数:
        *perm_codes: 可变数量的权限代码，例如 "doc.read"
        scope_builder: 一个可调用对象，接收Request并返回作用域键字符串

    返回:
        一个FastAPI依赖函数，可用于Depends(...)
    """

    # 定义内部异步函数_dep，它将作为实际的依赖项被调用
    async def _dep(
            request: Request,  # FastAPI请求对象，用于获取当前请求信息
            user: User = Depends(get_current_user),  # 通过依赖注入获取当前登录用户
            db: AsyncSession = Depends(get_db),  # 通过依赖注入获取数据库会话
    ) -> User:  # 函数返回User对象，以便路由函数可以使用
        # 调用scope_builder函数，传入request，生成当前请求的作用域键
        scope_key = str(scope_builder(request))  # 用scope_builder根据request动态生成scope_key
        # 调用核心权限检查函数require_perms，验证用户是否拥有所需权限
        await require_perms(db, user=user, scope_key=scope_key,
                            perm_codes=list(perm_codes))  # 调用RBAC核心校验逻辑，不通过抛AppError
        return user  # 通过则把用户返回给路由函数，供后续使用

    return _dep  # 返回内部函数_dep，它就是一个可被Depends(...)使用的依赖函数