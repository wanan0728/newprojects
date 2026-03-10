# 9.1 app/main.py
# 应用主入口模块
#
# 这个文件是 FastAPI 应用的入口点，负责：
# - 配置应用生命周期（启动时初始化组件，关闭时清理资源）
# - 注册中间件（请求上下文、租户、CORS、安全头）
# - 注册路由（健康检查、认证、管理员）
# - 安装异常处理器和 OpenAPI 文档定制
# - 执行启动前检查并同步权限数据

# 从__future__导入annotations功能，让类型注解在运行时不会被评估
from __future__ import annotations

# 从contextlib导入asynccontextmanager，用于创建异步上下文管理器（生命周期）
from contextlib import asynccontextmanager

# 从fastapi导入FastAPI，用于创建应用实例
from fastapi import FastAPI
# 从redis.asyncio导入Redis，用于创建异步Redis客户端
from redis.asyncio import Redis

# 从异常处理器模块导入安装函数，用于注册全局异常处理器
from app.api.exception_handlers import install_exception_handlers
# 从健康检查路由模块导入路由器
from app.api.health import router as health_router
# 从CORS中间件模块导入安装函数
from app.api.middleware.cors import install_cors
# 从请求上下文中间件模块导入中间件类
from app.api.middleware.request_context import RequestContextMiddleware
# 从安全头中间件模块导入中间件类
from app.api.middleware.security_headers import SecurityHeadersMiddleware
# 从租户上下文中间件模块导入中间件类
from app.api.middleware.tenant import TenantContextMiddleware
# 从OpenAPI定制模块导入安装函数
from app.api.openapi import install_openapi
# 从启动检查模块导入检查函数
from app.api.startup_checks import run_startup_checks
# 从配置模块导入settings对象，包含所有配置
from app.core.config import settings
# 从日志设置模块导入日志配置函数
from app.core.logging_setup import setup_logging
# 从数据库引擎模块导入引擎创建函数
from app.infra.db.engine import create_engine
# 从数据库会话模块导入会话工厂创建函数
from app.infra.db.session import create_session_maker
# 从Elasticsearch客户端模块导入客户端创建函数
from app.infra.elasticsearch_client import create_es_client
# 从管理员路由模块导入路由器
from app.modules.admin.routes import router as admin_router
# 从认证路由模块导入路由器
from app.modules.authn.routes import router as auth_router
# 从权限种子同步模块导入同步函数
from app.modules.authz.seed_sync import sync_authz


# 定义异步上下文管理器 lifespan，用于管理应用的生命周期
@asynccontextmanager
async def lifespan(application: FastAPI):
    # 这个函数主要开启日志，启动各个组件，将权限sync_authz插入数据库

    # 配置日志系统，使用配置中的日志级别
    setup_logging(level=settings.log_level)

    # 创建数据库引擎
    engine = create_engine()
    # 将引擎保存到应用状态中，供其他组件使用
    application.state.db_engine = engine
    # 创建数据库会话工厂，保存到应用状态
    application.state.db_session_maker = create_session_maker(engine)

    # 从配置创建Redis异步客户端
    redis = Redis.from_url(
        settings.redis_url,                                   # Redis连接URL
        decode_responses=False,                               # 不自动解码响应（保留字节，由业务决定）
        max_connections=settings.redis_max_connections,       # 最大连接数
        socket_connect_timeout=settings.redis_socket_connect_timeout,  # 连接超时
        socket_timeout=settings.redis_socket_timeout,         # 读写超时
        retry_on_timeout=True,                                 # 超时重试
        health_check_interval=settings.redis_health_check_interval,  # 健康检查间隔
    )
    # 将Redis客户端保存到应用状态
    application.state.redis = redis

    # 创建Elasticsearch客户端并保存到应用状态
    application.state.es = create_es_client()

    # 执行启动前检查，验证配置和依赖服务是否就绪
    await run_startup_checks(application)

    # 如果配置允许自动同步权限数据
    if settings.auto_sync_authz:
        # 创建数据库会话
        async with application.state.db_session_maker() as db:
            # 同步角色和权限种子数据到数据库
            await sync_authz(db)

    # yield 之前的代码在应用启动时执行
    yield
    # yield 之后的代码在应用关闭时执行

    # 关闭Elasticsearch客户端
    try:
        await application.state.es.close()
    except Exception:
        pass  # 忽略关闭时的异常

    # 关闭Redis客户端
    try:
        aclose = getattr(application.state.redis, "aclose", None)  # 尝试获取aclose方法
        if callable(aclose):
            await aclose()  # 如果存在aclose，调用它
        else:
            await application.state.redis.close()  # 否则调用close
    except Exception:
        pass  # 忽略关闭时的异常

    # 关闭数据库引擎，释放连接池
    try:
        await application.state.db_engine.dispose()
    except Exception:
        pass  # 忽略关闭时的异常


# 创建FastAPI应用实例，设置标题和生命周期管理器
app = FastAPI(title=settings.app_name, lifespan=lifespan)

# 添加请求上下文中间件（处理请求ID、审计上下文等）
app.add_middleware(RequestContextMiddleware)
# 添加租户上下文中间件（从请求中提取workspace_id）
app.add_middleware(TenantContextMiddleware)

# 安装全局异常处理器
install_exception_handlers(app)

# 安装CORS中间件，使用配置中的CORS设置
install_cors(
    app,
    allow_origins=settings.cors_origins_list(),        # 允许的源列表
    allow_credentials=settings.cors_allow_credentials, # 是否允许携带凭证
    allow_methods=settings.cors_methods_list(),        # 允许的HTTP方法
    allow_headers=settings.cors_headers_list(),        # 允许的请求头
)

# 如果启用了安全响应头，添加安全头中间件
if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware, content_security_policy=settings.csp)

# 注册健康检查路由（/healthz, /readyz, /version）
app.include_router(health_router)
# 注册认证路由（/auth/*）
app.include_router(auth_router)
# 注册管理员路由（/admin/*）
app.include_router(admin_router)

# 安装自定义OpenAPI文档生成器，添加通用响应头和错误模型
install_openapi(app)