# 4.9 app/api/middleware/cors.py
# CORS跨域资源共享中间件安装模块
#
# 这个文件提供了安装CORS中间件的函数，用于处理跨域请求。
# CORS（Cross-Origin Resource Sharing）是一种安全机制，允许网页从不同源（域名、协议、端口）请求资源。
# 当前端应用和后端API部署在不同的域名/端口时，需要正确配置CORS。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi.middleware.cors导入CORSMiddleware类
# CORSMiddleware是FastAPI内置的CORS中间件，用于处理跨域请求的响应头
from fastapi.middleware.cors import CORSMiddleware


# 定义install_cors函数，用于安装CORS中间件到FastAPI应用
# app: FastAPI应用实例
# *: 星号表示后面的参数必须用关键字方式传递
# allow_origins: list[str] 允许的源列表，如["http://localhost:3000", "https://example.com"]
# allow_credentials: bool 是否允许携带凭证（cookies、授权头等）
# allow_methods: list[str] 允许的HTTP方法，如["GET", "POST", "PUT", "DELETE"]
# allow_headers: list[str] 允许的请求头，如["Authorization", "Content-Type"]
# -> None 无返回值
def install_cors(
        app,
        *,
        allow_origins: list[str],
        allow_credentials: bool,
        allow_methods: list[str],
        allow_headers: list[str],
) -> None:
    """
    安装CORS中间件到FastAPI应用

    参数说明：
        app: FastAPI应用实例
        allow_origins: 允许访问的源列表（域名+端口）
        allow_credentials: 是否允许跨域请求携带凭证（cookies、认证头）
        allow_methods: 允许的HTTP方法列表
        allow_headers: 允许的请求头列表

    示例：
        install_cors(
            app,
            allow_origins=["http://localhost:3000", "https://example.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        )
    """
    # 调用app.add_middleware方法添加中间件
    # add_middleware是FastAPI应用的方法，用于注册中间件
    app.add_middleware(
        CORSMiddleware,  # 要添加的中间件类
        # 以下参数会传递给CORSMiddleware的构造函数
        allow_origins=allow_origins,  # 允许的源列表
        allow_credentials=allow_credentials,  # 是否允许携带凭证
        allow_methods=allow_methods,  # 允许的HTTP方法
        allow_headers=allow_headers,  # 允许的请求头
    )

    # CORSMiddleware的工作原理：
    # 1. 对于预检请求（OPTIONS方法），自动返回适当的CORS头
    # 2. 对于实际请求，添加Access-Control-Allow-Origin等响应头
    # 3. 根据配置验证请求的Origin是否在允许列表中