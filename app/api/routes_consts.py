# 4.1 app/api/routes_consts.py
# API路由常量定义模块
#
# 这个文件定义了与API路由相关的常量，主要用于控制路由的行为，
# 比如哪些路径不应该被缓存。将路由常量集中管理，便于统一维护和修改。

# 定义NO_STORE_PATHS集合，存储不应该被缓存的API路径
# 使用集合（set）而不是列表（list），因为集合的查找速度更快（O(1)）
# 这些路径产生的信息不要被浏览器或者任何其它中间件缓存
NO_STORE_PATHS = {
    # 认证相关路径 - 涉及用户登录状态，绝对不能缓存
    "/auth/login",  # 登录接口：包含用户名密码，不能缓存
    "/auth/refresh",  # 刷新令牌接口：生成新的token，不能缓存
    "/auth/logout",  # 登出接口：清除登录状态，不能缓存
    "/auth/me",  # 获取当前用户信息：每个用户信息不同，不能缓存
    "/auth/register",  # 注册接口：创建新用户，不能缓存

    # 管理员授权路径 - 涉及权限变更，不能缓存
    "/admin/grants",  # 管理员要给其它用户授权，权限变更必须实时生效

    # 为什么这些路径不能缓存？
    # 1. 安全性：包含敏感信息（密码、token）
    # 2. 实时性：涉及状态变更（登录、登出、授权）
    # 3. 个性化：每个用户返回的内容不同（/auth/me）
    # 4. 幂等性：有些操作每次执行结果可能不同
}

# 使用示例（在中间件中）：
# from app.api.routes_consts import NO_STORE_PATHS
#
# if request.url.path in NO_STORE_PATHS:
#     response.headers["Cache-Control"] = "no-store"