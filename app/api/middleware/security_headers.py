# 4.10 app/api/middleware/security_headers.py
# 安全响应头中间件模块
#
# 这个中间件负责为所有HTTP响应添加安全相关的响应头。
# 安全头可以防范常见的Web安全漏洞，如点击劫持、MIME类型嗅探、XSS攻击等。
# 通过配置这些头，可以提高应用的安全性。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi导入Request类，用于获取请求信息
from fastapi import Request
# 从starlette.middleware.base导入BaseHTTPMiddleware，用于创建中间件
from starlette.middleware.base import BaseHTTPMiddleware

# 从安全默认值模块导入安全头的默认配置
from app.core.security_defaults import (
    DEFAULT_HSTS_MAX_AGE,  # HSTS默认最大存活时间（1年）
    DEFAULT_PERMISSIONS_POLICY,  # 权限策略默认值（禁止地理位置、麦克风、摄像头）
    DEFAULT_REFERRER_POLICY,  # Referrer策略默认值（no-referrer）
    DEFAULT_X_FRAME_OPTIONS,  # X-Frame-Options默认值（DENY）
)


# 定义SecurityHeadersMiddleware类，继承自BaseHTTPMiddleware
# 这个中间件会在每个响应中添加各种安全头
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    # 定义__init__方法，初始化中间件配置
    # app: FastAPI应用实例
    # *: 星号表示后面的参数必须用关键字方式传递
    # hsts: bool 是否启用HSTS（HTTP Strict Transport Security）
    # hsts_max_age: int HSTS最大存活时间（秒）
    # include_subdomains: bool 是否包含子域名
    # preload: bool 是否加入HSTS预加载列表
    # x_content_type_options: bool 是否启用X-Content-Type-Options
    # x_frame_options: str X-Frame-Options的值
    # referrer_policy: str Referrer-Policy的值
    # permissions_policy: str Permissions-Policy的值
    # content_security_policy: str | None Content-Security-Policy的值
    def __init__(
            self,
            app,
            *,
            hsts: bool = True,
            hsts_max_age: int = DEFAULT_HSTS_MAX_AGE,
            include_subdomains: bool = True,
            preload: bool = False,
            x_content_type_options: bool = True,
            x_frame_options: str = DEFAULT_X_FRAME_OPTIONS,
            referrer_policy: str = DEFAULT_REFERRER_POLICY,
            permissions_policy: str = DEFAULT_PERMISSIONS_POLICY,
            content_security_policy: str | None = None,
    ):
        # 调用父类BaseHTTPMiddleware的__init__方法
        super().__init__(app)

        # 保存配置参数到实例变量
        self.hsts = hsts  # HSTS启用标志
        self.hsts_max_age = hsts_max_age  # HSTS最大存活时间
        self.include_subdomains = include_subdomains  # 是否包含子域名
        self.preload = preload  # 是否启用预加载
        self.x_content_type_options = x_content_type_options  # X-Content-Type-Options启用标志
        self.x_frame_options = x_frame_options  # X-Frame-Options的值
        self.referrer_policy = referrer_policy  # Referrer-Policy的值
        self.permissions_policy = permissions_policy  # Permissions-Policy的值
        self.csp = content_security_policy  # Content-Security-Policy的值

    # 重写dispatch方法，这是中间件的核心方法
    # request: Request 请求对象
    # call_next: 调用下一个中间件或路由处理函数
    async def dispatch(self, request: Request, call_next):
        # 调用下一个中间件或路由处理函数，获取响应
        resp = await call_next(request)

        # === 1. 添加HSTS头（Strict-Transport-Security）===
        # 这个头告诉浏览器只能通过HTTPS访问网站，禁止使用HTTP
        # 只有启用HSTS且当前请求是HTTPS时才添加
        if self.hsts and request.url.scheme == "https":
            # 基础值：max-age=秒数
            v = f"max-age={int(self.hsts_max_age)}"
            # 如果包含子域名，添加includeSubDomains指令
            if self.include_subdomains:
                v += "; includeSubDomains"
            # 如果启用预加载，添加preload指令
            if self.preload:
                v += "; preload"
            # 设置响应头
            resp.headers["Strict-Transport-Security"] = v

        # === 2. 添加X-Content-Type-Options头 ===
        # 这个头禁止浏览器嗅探MIME类型，防止基于MIME类型混淆的攻击
        # 值为"nosniff"表示严格按照Content-Type头处理
        if self.x_content_type_options:
            resp.headers["X-Content-Type-Options"] = "nosniff"

        # === 3. 添加X-Frame-Options头 ===
        # 这个头控制当前页面是否可以被嵌入到frame/iframe中，防止点击劫持攻击
        # 可选值：DENY（禁止所有）、SAMEORIGIN（只允许同源）
        if self.x_frame_options:
            resp.headers["X-Frame-Options"] = self.x_frame_options

        # === 4. 添加Referrer-Policy头 ===
        # 这个头控制在跳转时是否发送来源信息（referrer）
        # 可选值：no-referrer、same-origin、strict-origin等
        if self.referrer_policy:
            resp.headers["Referrer-Policy"] = self.referrer_policy

        # === 5. 添加Permissions-Policy头 ===
        # 这个头控制浏览器是否允许网页使用某些敏感功能
        # 如：地理位置、麦克风、摄像头、支付等
        if self.permissions_policy:
            resp.headers["Permissions-Policy"] = self.permissions_policy

        # === 6. 添加Content-Security-Policy头 ===
        # 这个头定义内容安全策略，限制资源加载来源，防止XSS攻击
        # 如：default-src 'self'、script-src 'self'等
        if self.csp:
            resp.headers["Content-Security-Policy"] = self.csp

        # 返回添加了安全头的响应
        return resp