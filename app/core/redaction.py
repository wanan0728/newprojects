# 1.8 app/core/redaction.py
# 敏感信息脱敏模块
#
# 这个文件的作用是在记录日志或返回错误信息时，自动过滤掉敏感数据（如密码、token等）。
# 防止密码、令牌等敏感信息被意外打印到日志文件或返回给客户端，提高系统安全性。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 导入Python的正则表达式模块
# re模块提供了正则表达式的支持，用于在字符串中查找和替换匹配特定模式的文本
import re
# 从typing模块导入Any类型
# Any表示任意类型，因为脱敏函数需要处理各种类型的数据
from typing import Any

# 编译正则表达式：匹配Bearer token
# re.compile() 预编译正则表达式，提高匹配效率
# r"\bBearer\s+([A-Za-z0-9\-._~+/]+=*)" 的解释：
#   \b 表示单词边界，确保匹配的是完整的Bearer单词
#   Bearer 匹配文本"Bearer"
#   \s+ 匹配一个或多个空白字符
#   [A-Za-z0-9\-._~+/]+ 匹配一个或多个URL安全的Base64字符
#   =* 匹配0个或多个等号（Base64填充字符）
# re.IGNORECASE 忽略大小写，可以匹配"Bearer"、"bearer"、"BEARER"等
_RE_BEARER = re.compile(r"\bBearer\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE)

# 编译正则表达式：匹配JWT token
# JWT格式通常为：xxxxx.yyyyy.zzzzz，由三部分组成，每部分都是Base64编码
# \b 单词边界，确保匹配的是独立的JWT
# eyJ 是JWT开头的常见模式（因为"eyJ"是Base64编码的JSON开头）
# [A-Za-z0-9_-]+=* 匹配第一部分（Base64字符，可能有填充=）
# \. 匹配点号分隔符
# [A-Za-z0-9_-]+=* 匹配第二部分
# \. 匹配点号分隔符
# [A-Za-z0-9_-]+=* 匹配第三部分
# \b 单词边界
_RE_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+=*\.[A-Za-z0-9_-]+=*\.[A-Za-z0-9_-]+=*\b")
# JWT确实是以eyJ开头的（这是Base64编码的JSON的开头特征）

# 定义敏感键名的集合
# 这些是字典中可能包含敏感信息的键名
SENSITIVE_KEYS = {
    "password",  # 密码
    "passwd",  # 密码的另一种写法
    "pwd",  # 密码的缩写
    "secret",  # 密钥
    "jwt",  # JWT令牌
    "token",  # 令牌
    "access_token",  # 访问令牌
    "refresh_token",  # 刷新令牌
    "authorization",  # 认证头
}


# 定义字符串脱敏函数
# s: str 输入字符串
# -> str 返回脱敏后的字符串
def redact_str(s: str) -> str:
    # 使用正则表达式替换Bearer token
    # _RE_BEARER.sub("Bearer ***", s) 在字符串s中查找所有匹配_BEARER模式的部分
    # 将找到的"Bearer 实际token"替换为"Bearer ***"
    s = _RE_BEARER.sub("Bearer ***", s)

    # 使用正则表达式替换JWT token
    # 将找到的JWT字符串替换为"***.***.***"
    s = _RE_JWT.sub("***.***.***", s)

    # 返回处理后的字符串
    return s


# 定义对象脱敏函数（递归处理各种数据类型）
# obj: Any 输入对象，可以是任何类型
# -> Any 返回脱敏后的对象
def redact_obj(obj: Any) -> Any:
    # 如果对象是None，直接返回None
    if obj is None:
        return None

    # 如果对象是字符串，调用redact_str处理
    if isinstance(obj, str):
        return redact_str(obj)

    # 如果对象是数字类型（整数、浮点数、布尔值），直接返回原值
    # 这些类型不包含敏感信息，不需要脱敏
    if isinstance(obj, (int, float, bool)):
        return obj

    # 如果对象是列表，递归处理列表中的每个元素
    # 返回一个新的列表，每个元素都是脱敏后的值
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]

    # 如果对象是元组，递归处理元组中的每个元素
    # 返回一个新的元组，每个元素都是脱敏后的值
    if isinstance(obj, tuple):
        return tuple(redact_obj(x) for x in obj)

    # 如果对象是字典，处理字典中的每个键值对
    if isinstance(obj, dict):
        # 创建一个新的空字典，用于存储脱敏后的结果
        out: dict[Any, Any] = {}

        # 遍历原字典的每个键值对
        for k, v in obj.items():
            # 将键保存到kk变量
            kk = k

            # 如果键是字符串，检查是否是敏感键名
            if isinstance(kk, str):
                # 将键转换为小写，以便不区分大小写地匹配
                kl = kk.lower()
                # 如果小写后的键名在敏感键名集合中
                if kl in SENSITIVE_KEYS:
                    # 将该键对应的值替换为"***"
                    out[kk] = "***"
                    # 跳过后续处理，继续下一个键值对
                    continue

            # 如果不是敏感键，递归处理值（值可能也是嵌套的数据结构）
            out[kk] = redact_obj(v)

        # 返回脱敏后的字典
        return out

    # 如果对象是其他类型（如自定义类的实例），直接返回原对象
    # 因为不知道如何处理，所以保持原样
    return obj