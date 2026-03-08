# 6.2 app/modules/authn/schemas.py
# 认证模块数据模型定义
#
# 这个文件定义了认证相关的API请求和响应的数据模型。
# 包括注册、登录、刷新令牌、获取用户信息等接口的请求/响应格式。
# 使用Pydantic模型进行数据验证和序列化。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从pydantic导入数据验证相关的类
# BaseModel: 所有Pydantic模型的基类
# EmailStr: 自动验证邮箱格式的字符串类型
# Field: 用于定义字段的验证规则，如最小长度、最大长度
from pydantic import BaseModel, EmailStr, Field


# 定义RegisterReq类，注册请求模型
class RegisterReq(BaseModel):
    """
    用户注册请求体

    属性:
        email: 用户邮箱，必须是有效的邮箱格式
        password: 密码，长度8-72位
    """
    # EmailStr类型会自动验证邮箱格式
    email: EmailStr

    # Field用于添加验证规则
    # min_length=8: 密码最少8位
    # max_length=72: 密码最多72位（bcrypt/argon2限制）
    password: str = Field(min_length=8, max_length=72)


# 定义LoginReq类，登录请求模型
class LoginReq(BaseModel):
    """
    用户登录请求体

    属性:
        email: 用户邮箱，必须是有效的邮箱格式
        password: 用户密码（明文）
    """
    email: EmailStr  # 邮箱，自动验证格式
    password: str  # 密码，不在这里验证长度（让后端验证更灵活）


# 定义TokenResp类，令牌响应模型
class TokenResp(BaseModel):
    """
    登录和刷新返回token的响应体

    属性:
        access_token: 访问令牌，用于API请求认证
        token_type: 令牌类型，固定为"bearer"
        expires_in_minutes: 访问令牌过期时间（分钟）
        refresh_token: 刷新令牌，用于获取新的访问令牌
    """
    access_token: str  # 访问令牌字符串
    token_type: str = "bearer"  # 令牌类型，默认bearer（Bearer Token认证）
    expires_in_minutes: int  # 过期时间（分钟），客户端可以用来提前刷新
    refresh_token: str  # 刷新令牌


# 定义RefreshReq类，刷新请求模型
class RefreshReq(BaseModel):
    """
    刷新和登出请求体

    属性:
        refresh_token: 刷新令牌
    """
    # 刷新的时候要提供的内容
    refresh_token: str  # 刷新令牌，用于获取新的访问令牌或登出


# 定义MeResp类，当前用户信息响应模型
class MeResp(BaseModel):
    """
    我的，响应

    返回当前登录用户的信息

    属性:
        id: 用户ID
        email: 用户邮箱
        is_active: 用户是否激活
        is_superadmin: 是否为超级管理员
    """
    id: int  # 用户ID
    email: EmailStr  # 用户邮箱，自动验证格式
    is_active: bool  # 是否激活（如果被禁用，不能登录）
    is_superadmin: bool  # 是否为超级管理员（拥有所有权限）