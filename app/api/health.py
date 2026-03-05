# 4.5 app/api/health.py
# 健康检查接口模块
#
# 这个代码是项目启动后，每隔一段时间或者利用外部工具来检测项目本身、中间件是否正常而使用的。
# 提供了三个接口：/healthz（应用存活检查）、/readyz（依赖服务就绪检查）、/version（版本信息）。
# 这些接口通常被容器编排工具（如Kubernetes）或监控系统调用，用于判断服务状态。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi导入APIRouter和Request
# APIRouter: 用于创建路由分组
# Request: FastAPI请求对象
from fastapi import APIRouter, Request

# 从redis.exceptions导入RedisError，用于捕获Redis异常
from redis.exceptions import RedisError

# 从sqlalchemy导入text，用于执行原生SQL语句
from sqlalchemy import text
# 从sqlalchemy.exc导入SQLAlchemyError，用于捕获数据库异常
from sqlalchemy.exc import SQLAlchemyError

# 从API响应模块导入ok函数，用于格式化成功响应
from app.core.api_response import ok
# 从API模式模块导入ApiResponse模型，用于响应类型声明
from app.core.api_schemas import ApiResponse
# 从配置模块导入settings，用于获取应用信息
from app.core.config import settings

# 创建一个APIRouter实例，用于注册健康检查相关的路由
# tags=["system"] 表示这个路由分组在API文档中归类为"system"
router = APIRouter(tags=["system"])


# 定义/healthz接口，用于存活检查（Liveness Probe）
# response_model=ApiResponse[dict] 指定响应格式为ApiResponse，数据部分为字典
@router.get("/healthz", response_model=ApiResponse[dict])
async def healthz():
    """
    存活检查接口 - 只负责保证FastAPI应用本身正常运行

    这个接口应该永远返回成功，除非应用完全挂了。
    只要FastAPI还能处理请求，就返回ok。
    """
    # 这个函数只负责保证FastAPI正常运行和返回
    # 返回 {"data": {"ok": True}} 格式
    return ok({"ok": True})


# 定义/readyz接口，用于就绪检查（Readiness Probe）
# response_model=ApiResponse[dict] 指定响应格式
@router.get("/readyz", response_model=ApiResponse[dict])
async def readyz(request: Request):
    """
    就绪检查接口 - 用于检测各个中间件（数据库、Redis、Elasticsearch）是否正常

    只有当所有依赖的服务都正常工作时，才返回成功。
    如果某个依赖服务不可用，返回失败，负载均衡器会停止向这个实例转发流量。
    """
    # 初始化各个服务的状态为False
    db_ok = False  # 数据库状态
    redis_ok = False  # Redis状态
    es_ok = False  # Elasticsearch状态

    # 检查数据库连接是否正常
    try:
        # 从应用状态中获取数据库会话工厂
        session_maker = request.app.state.db_session_maker
        # 创建数据库会话
        async with session_maker() as session:
            # 执行简单的SELECT 1语句，测试数据库连接
            # 如果能执行成功，说明数据库正常
            await session.execute(text("SELECT 1"))
        db_ok = True  # 执行成功，标记数据库正常
    except (AttributeError, SQLAlchemyError):
        # 捕获异常：AttributeError（db_session_maker不存在）或SQLAlchemyError（数据库错误）
        # 不做任何处理，db_ok保持False
        pass

    # 检查Redis连接是否正常
    try:
        # 从应用状态中获取Redis客户端
        redis = request.app.state.redis
        # 执行ping命令，测试Redis连接
        # redis.ping() 如果连接正常会返回True
        await redis.ping()
        redis_ok = True  # ping成功，标记Redis正常
    except (AttributeError, RedisError, TimeoutError, OSError):
        # 捕获各种可能的异常：Redis客户端不存在、Redis错误、超时、操作系统错误
        # redis_ok保持False
        pass

    # 检查Elasticsearch连接是否正常
    try:
        # 从应用状态中获取ES客户端
        es = request.app.state.es
        # 执行ping命令，测试ES连接
        # es.ping() 返回布尔值，用bool()确保转换为布尔类型
        es_ok = bool(await es.ping())
    except Exception:
        # 捕获任何异常，标记ES为不可用
        es_ok = False

    # 判断所有服务是否都正常
    # 只有db、redis、es都正常，ok_all才为True
    ok_all = bool(db_ok and redis_ok and es_ok)

    # 返回检查结果
    return ok({
        "ok": ok_all,  # 整体状态
        "deps": {  # 各个依赖服务的详细状态
            "db": db_ok,
            "redis": redis_ok,
            "es": es_ok
        }
    })


# 定义/version接口，用于获取应用版本信息
# response_model=ApiResponse[dict] 指定响应格式
@router.get("/version", response_model=ApiResponse[dict])
async def version():
    """
    版本信息接口 - 返回应用名称和当前运行环境

    用于在部署和运维时确认当前版本和环境。
    """
    # 返回应用信息
    return ok({
        "app": settings.app_name,  # 应用名称，如 "enterprise-assistant"
        "env": settings.env  # 运行环境，如 "dev", "prod"等
    })