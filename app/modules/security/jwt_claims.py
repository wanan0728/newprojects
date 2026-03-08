# 5.2 app/modules/security/jwt_claims.py
# JWT声明（Claims）常量定义模块
#
# 这个文件定义了JWT（JSON Web Token）中使用的声明字段名。
# JWT由三部分组成：Header.Payload.Signature，Payload中的每个字段称为Claim。
# 将这些字段名定义为常量，可以避免在代码中硬编码字符串，减少拼写错误。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 定义CLAIM_ISS常量，对应JWT标准中的"iss" (Issuer) 声明
# 表示JWT的签发者，通常填域名或应用名称
# 例如：{"iss": "enterprise-assistant"}
CLAIM_ISS = "iss"  # 签发者

# 定义CLAIM_SUB常量，对应JWT标准中的"sub" (Subject) 声明
# 表示JWT的主题，通常填用户ID
# 在我们的项目里用作user_id
# 例如：{"sub": 12345}
CLAIM_SUB = "sub"  # JWT的标准字段subject，我们的项目里用作user_id

# 定义CLAIM_VER常量，自定义的"ver" (Version) 声明
# 表示JWT的版本号，用于实现令牌吊销功能
# 当用户修改密码或登出时，可以增加版本号，使旧令牌失效
# 例如：{"ver": 2}
CLAIM_VER = "ver"  # token version

# 定义CLAIM_TYP常量，自定义的"typ" (Type) 声明
# 表示JWT的类型，区分是访问令牌还是刷新令牌
# 例如：{"typ": "access"} 或 {"typ": "refresh"}
CLAIM_TYP = "typ"  # token类型，比如access or refresh

# 定义CLAIM_IAT常量，对应JWT标准中的"iat" (Issued At) 声明
# 表示JWT的签发时间，Unix时间戳格式
# 用于判断令牌何时签发
# 例如：{"iat": 1741353600}
CLAIM_IAT = "iat"  # 签发时间

# 定义CLAIM_EXP常量，对应JWT标准中的"exp" (Expiration Time) 声明
# 表示JWT的过期时间，Unix时间戳格式
# 超过这个时间，令牌自动失效
# 例如：{"exp": 1741357200}
CLAIM_EXP = "exp"  # 过期时间

# 定义TOKEN_TYPE_ACCESS常量，表示访问令牌类型
# 用于CLAIM_TYP字段的值
# 访问令牌用于API请求认证，有效期短（如30分钟）
TOKEN_TYPE_ACCESS = "access"

# 完整的JWT Payload示例：
# {
#     "iss": "enterprise-assistant",     # 签发者
#     "sub": "12345",                     # 用户ID
#     "ver": 1,                            # 令牌版本
#     "typ": "access",                     # 令牌类型
#     "iat": 1741353600,                   # 签发时间
#     "exp": 1741357200                    # 过期时间
# }