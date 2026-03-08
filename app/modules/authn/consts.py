# 6.1 app/modules/authn/consts.py
# 认证模块常量定义
#
# 这个文件定义了认证模块中使用的所有常量。
# 包括刷新令牌格式、Redis键前缀、限流规则名称等。
# 将常量集中管理，避免在代码中硬编码字符串，减少拼写错误。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 定义刷新令牌的分隔符
# 刷新令牌通常由两部分组成：RID（随机ID）和SECRET（密钥）
# 用分隔符连接，格式如： "abc123.def456"
# refresh token的分隔符
REFRESH_SEPARATOR = "."

# 定义刷新令牌的最大长度
# 刷新令牌由RID和SECRET组成，总长度不能超过这个值
# 4096字节足够存储任何组合的RID和SECRET
MAX_REFRESH_TOKEN_LEN = 4096

# 定义RID段的最大长度
# RID是刷新令牌的标识部分，用于在Redis中查找对应的令牌信息
# UUID的实际长度是36，这里预留更多空间
# rid段最大长度，uuid实际是36，这里有多余的
MAX_RID_LEN = 64

# 定义SECRET段的最大长度
# SECRET是刷新令牌的密钥部分，用于验证令牌的真实性
# secret段最大长度
MAX_SECRET_LEN = 256

# 定义刷新令牌的Redis键前缀
# 用于存储在Redis中的刷新令牌信息
# 完整的键名格式： auth:refresh:{rid}
# redis key的前缀，这里是刷新令牌
REDIS_PREFIX_REFRESH = "auth:refresh:"

# 定义令牌版本的Redis键前缀
# 用于存储用户的令牌版本号，实现令牌吊销功能
# 当用户修改密码或登出时，增加版本号，使旧令牌失效
# 完整的键名格式： auth:tokenver:{user_id}
# 也是redis key的前缀，这里是access token失效
REDIS_PREFIX_TOKENVER = "auth:tokenver:"

# 定义注册接口的限流规则名称
# 用于限制同一IP在单位时间内的注册次数
# 注册限流
RL_AUTH_REGISTER = "auth_register"

# 定义登录接口的限流规则名称
# 用于限制同一IP在单位时间内的登录尝试次数
# 防止暴力破解密码
# 登录限流
RL_AUTH_LOGIN = "auth_login"

# 定义刷新令牌接口的限流规则名称
# 用于限制同一IP在单位时间内的刷新令牌请求次数
# 刷新限流
RL_AUTH_REFRESH = "auth_refresh"