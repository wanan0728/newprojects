# 1.5 app/core/error_codes.py
# 错误码定义模块
#
# 该文件集中定义了项目中所有的错误码、对应的错误消息和HTTP状态码。
# 统一管理错误码可以确保整个项目使用一致的错误标识，方便前端处理和问题排查。


# 开启前向引用，允许在类型提示中使用字符串形式的类型名
from __future__ import annotations

# 错误消息映射字典：错误码 -> 用户看到的错误提示
# 键是程序内部使用的错误码，值是返回给客户端的错误信息
ERROR_MESSAGES: dict[str, str] = {
    # 基础错误类
    "error.validation_failed": "validation_failed",      # 数据验证失败（如邮箱格式不对）
    "error.internal": "internal_error",                  # 服务器内部错误（未知异常）
    "error.http": "http_error",                          # HTTP请求错误
    "error.rate_limited": "rate_limited",                # 请求太频繁，被限流了

    # 认证授权相关错误
    "auth.bearer_required": "Missing bearer token",      # 请求没带token
    "auth.access_token_invalid": "Invalid access token", # token无效（格式错误或伪造）
    "auth.access_token_expired": "Token expired",        # token过期了
    "auth.user_inactive": "User disabled or not found",  # 用户被禁用或不存在
    "auth.email_taken": "Email already exists",          # 注册时邮箱已被使用
    "auth.credentials_invalid": "Invalid credentials",   # 用户名或密码错误
    "auth.refresh_token_invalid": "Invalid refresh token", # refresh token无效
    "auth.refresh_token_expired": "Refresh expired",     # refresh token过期

    # 权限控制相关错误
    "rbac.forbidden": "forbidden",                        # 没有权限访问
    "rbac.role_required": "no_role",                      # 需要特定角色
    "rbac.permission_missing": "missing_perms",           # 缺少特定权限

    # 管理员功能相关错误
    "admin.role_not_found": "role not found",            # 角色不存在
    "admin.user_not_found": "user not found",            # 用户不存在

    # 数据存储相关错误
    "storage.db_error": "db_error",                       # 数据库操作失败
}

# HTTP状态码映射字典：错误码 -> 对应的HTTP状态码
# 客户端可以根据状态码快速判断错误类型（如401跳登录，403提示无权限）
ERROR_STATUS: dict[str, int] = {
    # 基础错误类
    "error.validation_failed": 422,   # 422 Unprocessable Entity：数据格式正确但内容不合要求
    "error.internal": 500,            # 500 Internal Server Error：服务器出问题了
    "error.http": 400,                # 400 Bad Request：请求本身有问题
    "error.rate_limited": 429,        # 429 Too Many Requests：请求太频繁

    # 认证授权相关错误
    "auth.bearer_required": 401,      # 401 Unauthorized：没登录或token无效
    "auth.access_token_invalid": 401, # 401：token无效
    "auth.access_token_expired": 401, # 401：token过期了，需要重新登录
    "auth.user_inactive": 401,        # 401：账号状态异常
    "auth.email_taken": 409,          # 409 Conflict：邮箱已被注册，冲突了
    "auth.credentials_invalid": 401,  # 401：账号或密码错误
    "auth.refresh_token_invalid": 401,# 401：refresh token无效
    "auth.refresh_token_expired": 401,# 401：refresh token过期，需要重新登录

    # 权限控制相关错误
    "rbac.forbidden": 403,            # 403 Forbidden：登录了但没权限
    "rbac.role_required": 403,        # 403：角色不符合要求
    "rbac.permission_missing": 403,   # 403：缺少具体权限

    # 管理员功能相关错误
    "admin.role_not_found": 404,      # 404 Not Found：要操作的角色不存在
    "admin.user_not_found": 404,      # 404：要操作用户不存在

    # 数据存储相关错误
    "storage.db_error": 500,          # 500：数据库操作失败
}