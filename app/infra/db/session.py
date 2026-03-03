# 2.3 app/infra/db/session.py
# 数据库会话工厂创建模块
#
# 这个文件负责创建SQLAlchemy的异步会话工厂（sessionmaker）。
# 会话（Session）是ORM与数据库交互的入口，用于执行查询、添加、删除等操作。
# 会话工厂的作用是生成新的会话实例，避免每次手动创建会话的重复代码。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从sqlalchemy.ext.asyncio模块导入异步会话相关类
# sqlalchemy是Python最流行的ORM库
# ext.asyncio是SQLAlchemy的异步扩展，支持异步数据库操作
# AsyncEngine: 异步引擎的类型，用于类型提示
# AsyncSession: 异步会话的类型，用于类型提示
# async_sessionmaker: 异步会话工厂类，用于创建AsyncSession实例
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


# 定义create_session_maker函数，用于创建异步会话工厂
# engine: AsyncEngine 参数，接收一个已经创建好的异步数据库引擎
# -> async_sessionmaker[AsyncSession]: 类型注解，表示返回一个专门创建AsyncSession的会话工厂
def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # 调用async_sessionmaker构造函数创建会话工厂
    # async_sessionmaker是SQLAlchemy提供的异步会话工厂类
    # 它会绑定到传入的引擎，后续通过这个工厂创建的会话都会使用这个引擎
    return async_sessionmaker(
        engine,  # 第一个参数：绑定的数据库引擎，会话将通过这个引擎连接数据库

        # expire_on_commit: 提交后是否过期
        # 设置为False表示提交事务后，会话中的对象不会自动过期
        # 这样在提交后仍然可以访问对象的属性，而不需要重新加载
        # 如果设置为True，提交后所有对象的属性都会过期，再次访问时会自动重新查询数据库
        expire_on_commit=False,

        # class_: 指定会话类
        # 这里明确指定使用AsyncSession类
        # 虽然async_sessionmaker默认就是创建AsyncSession，但显式指定更清晰
        class_=AsyncSession,
    )

    # 这个会话工厂创建后，可以这样使用：
    # session_maker = create_session_maker(engine)
    # async with session_maker() as session:
    #     result = await session.execute(select(...))