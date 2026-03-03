# 2.4 app/infra/db/deps.py
# 数据库会话依赖模块
#
# 这个文件定义了FastAPI的依赖项，用于在请求处理过程中获取数据库会话。
# 在项目中只要需要数据库连接的时候，都默认调用这个函数。
# 它会自动处理多租户隔离（通过设置PostgreSQL的会话变量），
# 并确保会话在使用后被正确关闭。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从typing模块导入AsyncGenerator
# AsyncGenerator: 异步生成器类型，用于类型提示
# 这个函数是异步生成器，会yield出数据库会话，然后在请求结束后清理
from typing import AsyncGenerator

# 从fastapi导入Request类
# Request: FastAPI的请求对象，包含了当前HTTP请求的所有信息
from fastapi import Request

# 从sqlalchemy导入text函数
# text: 用于创建原始SQL文本对象的函数，可以执行原生SQL语句
from sqlalchemy import text

# 从sqlalchemy.ext.asyncio导入AsyncSession
# AsyncSession: SQLAlchemy的异步会话类，用于执行异步数据库操作
from sqlalchemy.ext.asyncio import AsyncSession

# 从请求上下文模块导入get_workspace_id函数
# get_workspace_id: 从上下文中获取当前请求的工作空间ID
from app.core.request_context import get_workspace_id


# 定义get_db异步生成器函数，这是FastAPI的依赖项
# request: Request 参数，FastAPI会自动注入当前请求对象
# -> AsyncGenerator[AsyncSession, None]: 类型注解，表示这是一个异步生成器
#    生成的值是AsyncSession类型，最终返回None
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # 从请求对象的app.state中获取数据库会话工厂
    # request.app 是FastAPI应用实例
    # app.state 是应用级别的状态存储，可以在整个应用生命周期中共享数据
    # db_session_maker 是在应用启动时创建的会话工厂（在main.py中设置）
    session_maker = request.app.state.db_session_maker

    # 使用async with语句创建会话上下文
    # session_maker() 调用会话工厂创建新的会话实例
    # async with 确保会话在使用完毕后自动关闭
    async with session_maker() as session:
        # 尝试从请求状态中获取workspace_id
        # getattr(request.state, "workspace_id", None) 安全地获取属性，不存在则返回None
        wid = getattr(request.state, "workspace_id", None)

        # 如果请求状态中没有workspace_id
        if wid is None:
            # 从请求上下文中获取workspace_id
            # 这个上下文是在中间件中设置的
            wid = get_workspace_id()

        # 将workspace_id转换为字符串值
        # if wid is not None else "0": 如果有值就用它，否则用"0"
        # int(wid) 确保它是整数类型
        # str() 再转回字符串，因为set_config需要字符串参数
        wid_val = str(int(wid)) if wid is not None else "0"

        # 执行SQL语句设置PostgreSQL的会话变量
        # SELECT set_config('app.tenant_id', :v, false) 是PostgreSQL函数
        # set_config 用于设置配置参数，只在当前会话有效
        # 'app.tenant_id' 是自定义的配置参数名
        # :v 是参数占位符，后面用{"v": wid_val}传入实际值
        # false 表示这个设置只在当前事务中有效（如果true则对整个会话有效）
        await session.execute(
            text("SELECT set_config('app.tenant_id', :v, false)"),
            {"v": wid_val},
        )

        # 提交事务，使set_config生效
        # 注意：这里提交事务是为了让set_config立即生效
        # 后续的业务操作会在新的事务中执行
        await session.commit()

        # try-finally块确保即使发生异常也能正确清理
        try:
            # yield将会话对象返回给依赖它的路径操作函数
            # 这里的yield让这个函数成为生成器
            # FastAPI会执行到这里，将session注入到路径函数中
            yield session

        finally:
            # 不管业务代码是否抛出异常，最终都会执行到这里

            # 检查会话是否还在事务中
            # session.in_transaction() 判断当前是否有未提交的事务
            if session.in_transaction():
                # 如果还有未提交的事务，回滚它
                # 这通常发生在业务代码抛出异常导致事务未提交的情况
                await session.rollback()

            # 注意：不需要显式调用session.close()
            # async with 上下文管理器已经保证了会话会被关闭