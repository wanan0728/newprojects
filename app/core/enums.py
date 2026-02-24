# 1.2 app/core/enums.py
# 枚举常量定义
#
# 这个文件定义了项目中用到的各种"选项"，比如环境类型、加密算法等。
# 用枚举可以把散落在代码各处的字符串集中管理，避免写错字，也方便统一修改。


# 从enum模块导入Enum类
# enum是Python标准库中的一个模块，专门用于定义枚举
# Enum是这个模块中的基类，所有枚举类都需要继承它
from enum import Enum


# 定义Env类，继承自str和Enum
# class是定义类的关键字
# Env是类名，代表"Environment"（环境）
# (str, Enum) 表示这个类同时继承自str和Enum
# 继承str是为了让枚举值可以直接当字符串用，比如可以直接和字符串比较
# 继承Enum是为了获得枚举的特性（成员唯一、可遍历等）
class Env(str, Enum):
    """
    运行环境枚举 - 项目会在哪些环境下运行

    继承str是为了让枚举值可以直接当字符串用，比如 if env == "dev" 也能正常工作
    """
    # dev是枚举成员的名称，等号右边的"dev"是枚举成员的值
    # 这里定义了一个名为dev的枚举成员，对应的值是字符串"dev"
    # 代表开发环境：程序员写代码、本地调试用的
    dev = "dev"

    # prod是枚举成员名称，值是"prod"
    # 生产环境（简写）：正式对用户服务的环境
    prod = "prod"

    # production是枚举成员名称，值是"production"
    # 生产环境（完整拼写）：和上面一样，可能是为了兼容老系统
    production = "production"

    # staging是枚举成员名称，值是"staging"
    # 预发布环境：和正式环境一模一样，上线前最后测试用的
    staging = "staging"


# 定义JwtAlg类，同样继承自str和Enum
# JwtAlg是"JWT Algorithm"的缩写，代表JWT算法
class JwtAlg(str, Enum):
    """
    JWT签名算法枚举 - 加密token用的算法类型

    JWT是用户登录后发的令牌，需要签名防止篡改，不同算法安全级别不一样
    """
    # HS256是枚举成员名称，值是"HS256"
    # HS256：对称加密（加密解密用同一个密码）
    # 就像用同一把钥匙锁门和开门，速度快，适合内部系统
    HS256 = "HS256"

    # RS256是枚举成员名称，值是"RS256"
    # RS256：非对称加密（公钥加密，私钥解密）
    # 就像把锁（公钥）给别人，钥匙（私钥）自己留着，更安全，适合对外提供接口
    RS256 = "RS256"