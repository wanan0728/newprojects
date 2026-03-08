# 5.3 app/modules/security/jwt.py
# JWT令牌生成和验证模块
#
# 这个文件提供了JWT（JSON Web Token）的创建和解析功能。
# JWT用于用户认证，在用户登录后颁发，后续请求携带此令牌证明身份。
# 包含访问令牌的生成、解码和验证。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从dataclasses导入dataclass装饰器，用于定义数据类
# dataclass可以自动生成__init__、__repr__等方法
from dataclasses import dataclass

# 从datetime导入日期时间相关类
from datetime import datetime, timedelta, timezone

# 从typing导入Any，表示任意类型
from typing import Any

# 从jose导入JWT相关功能
# jose是一个处理JWT的库，支持多种加密算法
# JWTError: JWT相关的异常类
# jwt: JWT编解码的核心模块
from jose import JWTError, jwt

# 导入JWT声明常量
from app.modules.security.jwt_claims import (
    CLAIM_EXP,  # 过期时间
    CLAIM_IAT,  # 签发时间
    CLAIM_ISS,  # 签发者
    CLAIM_SUB,  # 主题（用户ID）
    CLAIM_TYP,  # 令牌类型
    CLAIM_VER,  # 令牌版本
    TOKEN_TYPE_ACCESS,  # 访问令牌类型
)


# 定义TokenPayload数据类，用于存储解码后的令牌信息
# @dataclass装饰器自动生成__init__、__repr__等方法
# frozen=True 表示这个类的实例是不可变的（只读），创建后不能修改
@dataclass(frozen=True)
class TokenPayload:
    """
    令牌载荷数据类，包含从JWT中解析出的信息

    属性:
        user_id: 用户ID
        token_ver: 令牌版本号（用于吊销）
        typ: 令牌类型（目前只有access）
    """
    user_id: int  # 用户ID，从sub字段解析得到
    token_ver: int  # 令牌版本，用于实现令牌吊销功能
    typ: str  # 令牌类型，目前只有"access"


# 定义create_access_token函数，生成访问令牌
# *: 星号表示后面的参数必须用关键字方式传递
# secret: str JWT密钥
# issuer: str 签发者
# alg: str 加密算法（如HS256）
# user_id: int 用户ID
# token_ver: int 令牌版本
# minutes: int 过期时间（分钟）
# -> str 返回JWT令牌字符串
def create_access_token(
        *,
        secret: str,
        issuer: str,
        alg: str,
        user_id: int,
        token_ver: int,
        minutes: int,
) -> str:
    """
    创建访问令牌

    参数说明（全部为关键字参数）：
        secret: JWT签名密钥
        issuer: 签发者标识
        alg: 加密算法
        user_id: 用户ID
        token_ver: 令牌版本
        minutes: 过期分钟数

    返回:
        JWT令牌字符串
    """
    # 获取当前UTC时间
    # timezone.utc 表示使用UTC时区，避免时区问题
    now = datetime.now(timezone.utc)

    # 构建JWT载荷（Payload）
    payload = {
        CLAIM_ISS: str(issuer),  # 签发者：转成字符串
        CLAIM_SUB: str(int(user_id)),  # 用户ID：确保是整数再转字符串
        CLAIM_VER: int(token_ver),  # 令牌版本：确保是整数
        CLAIM_TYP: TOKEN_TYPE_ACCESS,  # 令牌类型：固定为access
        CLAIM_IAT: int(now.timestamp()),  # 签发时间戳：当前时间的Unix时间戳
        CLAIM_EXP: int((now + timedelta(minutes=int(minutes))).timestamp()),  # 过期时间戳：当前时间 + minutes分钟
    }

    # 使用jwt.encode编码生成JWT字符串
    # payload: 载荷数据
    # secret: 密钥
    # algorithm: 加密算法
    return jwt.encode(payload, secret, algorithm=str(alg))


# 定义_must_int函数，确保从载荷中获取的值是整数
# payload: dict[str, Any] JWT载荷字典
# k: str 键名
# -> int 返回整数值
def _must_int(payload: dict[str, Any], k: str) -> int:
    """
    从载荷中获取指定键的值，并确保它是整数

    参数:
        payload: JWT载荷字典
        k: 键名，如CLAIM_SUB

    返回:
        整数值

    抛出:
        ValueError: 如果值不存在或无法转换为整数
    """
    # 确定载荷中是放的int，此处是用户id，即int类型

    # 从载荷中获取值
    v = payload.get(k)
    if v is None:
        # 值为空，抛出异常
        raise ValueError("invalid_token_payload")

    try:
        # 尝试转换为整数
        # 可能的值类型：int、str（如"123"）、float等
        return int(v)
    except Exception as e:
        # 转换失败，抛出异常
        # from e 保持异常链，便于调试
        raise ValueError("invalid_token_payload") from e


# 定义decode_access_token函数，解码和验证访问令牌
# token: str JWT令牌字符串
# secret: str 密钥
# issuer: str 预期的签发者
# alg: str 预期的加密算法
# leeway_seconds: int 时间容忍度（秒），默认30秒
# -> TokenPayload 返回令牌载荷
def decode_access_token(
        *,
        token: str,
        secret: str,
        issuer: str,
        alg: str,
        leeway_seconds: int = 30,
) -> TokenPayload:
    """
    解码并验证访问令牌

    参数:
        token: JWT令牌字符串
        secret: 密钥
        issuer: 预期的签发者
        alg: 加密算法
        leeway_seconds: 时间容忍度（秒），允许一定的时钟偏差

    返回:
        TokenPayload对象，包含用户ID、令牌版本等信息

    抛出:
        ValueError: 令牌无效、过期、类型错误等
    """
    try:
        # 设置验证选项
        options = {
            "verify_aud": False,  # 不验证audience（受众）
            "require_exp": True,  # 必须包含exp声明
            "require_sub": True,  # 必须包含sub声明
            "require_iss": True,  # 必须包含iss声明
            "leeway": int(leeway_seconds),  # 时间容忍度（秒）
        }

        # 调用jwt.decode解码和验证令牌
        payload = jwt.decode(
            token,  # JWT字符串
            secret,  # 密钥
            algorithms=[str(alg)],  # 允许的算法列表
            issuer=str(issuer),  # 预期的签发者
            options=options,  # 验证选项
        )
    except JWTError as e:
        # JWT验证失败（过期、签名错误、算法不匹配等）
        raise ValueError("invalid_token") from e

    # 确保载荷是字典类型
    if not isinstance(payload, dict):
        raise ValueError("invalid_token_payload")

    # 验证令牌类型是否为访问令牌
    if payload.get(CLAIM_TYP) != TOKEN_TYPE_ACCESS:
        raise ValueError("invalid_token_type")

    # 获取用户ID（确保是整数）
    user_id = _must_int(payload, CLAIM_SUB)

    # 获取令牌版本（确保是整数）
    token_ver = _must_int(payload, CLAIM_VER)

    # 获取签发时间（可选，但建议包含）
    iat = payload.get(CLAIM_IAT)
    if iat is None:
        raise ValueError("invalid_token_payload")

    # 返回TokenPayload对象
    return TokenPayload(
        user_id=int(user_id),  # 用户ID
        token_ver=int(token_ver),  # 令牌版本
        typ=TOKEN_TYPE_ACCESS  # 令牌类型
    )