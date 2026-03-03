# 2.5 app/infra/redis_client.py
# Redis客户端依赖模块
#
# 这个文件定义了获取Redis客户端的依赖函数。
# 在FastAPI应用中，可以通过这个函数在路径操作中获取已经配置好的Redis连接，
# 用于缓存、限流、分布式锁等场景。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从fastapi模块导入Request类
# Request: FastAPI的请求对象，包含了当前HTTP请求的所有信息
# 可以通过request.app访问FastAPI应用实例，进而访问应用级别的状态
from fastapi import Request

# 从redis.asyncio模块导入Redis类
# redis.asyncio是Redis官方提供的异步客户端
# Redis类提供了异步的Redis操作方法，如get、set、delete等
from redis.asyncio import Redis


# 定义get_redis函数，这是FastAPI的依赖项
# request: Request 参数，FastAPI会自动注入当前请求对象
# -> Redis: 类型注解，表示这个函数返回一个Redis客户端对象
def get_redis(request: Request) -> Redis:
    # 从请求对象的app.state中获取Redis客户端
    # request.app 是FastAPI应用实例
    # app.state 是应用级别的状态存储，可以在整个应用生命周期中共享数据
    # redis 是在应用启动时创建的Redis连接客户端（在main.py中设置）
    #
    # 这样设计的好处是：
    # 1. Redis客户端只需要创建一次（应用启动时），而不是每次请求都创建
    # 2. 所有请求共享同一个连接池，避免连接数过多
    # 3. 依赖注入让测试时更容易替换（比如替换为Mock对象）
    return request.app.state.redis

    # 使用示例（在路径操作函数中）：
    # from app.infra.redis_client import get_redis
    # from fastapi import Depends
    #
    # @app.get("/cache")
    # async def get_cache(redis: Redis = Depends(get_redis)):
    #     value = await redis.get("key")
    #     return {"value": value}