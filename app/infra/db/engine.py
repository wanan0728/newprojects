# 2.2 app/infra/db/engine.py
# 数据库引擎创建模块
#
# 这个文件负责创建SQLAlchemy的异步数据库引擎。
# 数据库引擎是ORM与数据库之间的连接核心，负责管理连接池、执行SQL语句等。
# 使用异步引擎可以提高并发处理能力，避免阻塞事件循环。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从sqlalchemy.ext.asyncio模块导入异步引擎相关类
# sqlalchemy是Python最流行的ORM库
# ext.asyncio是SQLAlchemy的异步扩展，支持异步数据库操作
# AsyncEngine: 异步引擎的类型，用于类型提示
# create_async_engine: 创建异步引擎的函数
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# 从应用的配置模块导入settings对象
# settings包含了所有应用配置，包括数据库连接信息
from app.core.config import settings


# 定义create_engine函数，用于创建并返回异步数据库引擎
# -> AsyncEngine: 类型注解，表示这个函数返回一个AsyncEngine对象
def create_engine() -> AsyncEngine:
    # 调用create_async_engine函数创建异步引擎
    # 这个函数是SQLAlchemy提供的异步引擎工厂函数
    return create_async_engine(
        # 第一个参数：数据库连接URL
        # 从配置中获取，格式如：postgresql+asyncpg://user:pass@localhost/dbname
        settings.database_url,

        # pool_pre_ping: 是否在从连接池获取连接前发送ping命令测试连接是否有效
        # 设置为True可以自动断开无效的连接，避免使用已断开的连接导致错误
        pool_pre_ping=True,

        # pool_size: 连接池的大小，即保持打开状态的连接数
        # 从配置的db_pool_size获取，默认10
        pool_size=settings.db_pool_size,

        # max_overflow: 连接池最大溢出连接数
        # 当连接池用完时，最多可以额外创建的连接数
        # 从配置的db_max_overflow获取，默认20
        max_overflow=settings.db_max_overflow,

        # pool_recycle: 连接回收时间（秒）
        # 连接使用超过这个时间后会被自动回收重建，防止连接过期
        # 从配置的db_pool_recycle获取，默认1800秒（30分钟）
        pool_recycle=settings.db_pool_recycle,

        # pool_timeout: 获取连接的超时时间（秒）
        # 当连接池中没有可用连接时，最多等待这个时间
        # 从配置的db_pool_timeout获取，默认30秒
        pool_timeout=settings.db_pool_timeout,
    )