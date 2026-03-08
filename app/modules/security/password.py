# 5.1 app/modules/security/password.py
# 密码哈希和验证模块
#
# 这个文件提供了密码的安全处理功能，包括哈希和验证。
# 使用 Argon2 算法，这是目前公认最安全的密码哈希算法，
# 在2015年密码哈希竞赛中获胜，被推荐用于密码存储。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从argon2模块导入PasswordHasher类
# argon2是一个第三方库，实现了Argon2密码哈希算法
# PasswordHasher是用于创建和验证密码哈希的类
from argon2 import PasswordHasher

# 从argon2.exceptions导入异常类
# VerifyMismatchError: 密码验证不匹配时抛出
# VerificationError: 验证过程中发生其他错误时抛出
from argon2.exceptions import VerifyMismatchError, VerificationError

# 创建PasswordHasher的实例，用于后续的哈希和验证操作
# 使用默认配置：
#   - time_cost=2 (迭代次数)
#   - memory_cost=102400 (内存成本)
#   - parallelism=8 (并行度)
#   - hash_len=32 (哈希长度)
#   - salt_len=16 (盐值长度)
# 下划线前缀表示这是模块内部使用的变量，不应该被外部直接访问
_ph = PasswordHasher()  # argon2密码散列器实例


# 定义hash_password函数，用于将原始密码哈希化
# raw: str 原始密码字符串
# -> str 返回哈希后的密码字符串
def hash_password(raw: str) -> str:
    """
    将原始密码进行Argon2哈希

    参数:
        raw: 用户输入的原始密码

    返回:
        哈希后的密码字符串，格式如：
        $argon2id$v=19$m=102400,t=2,p=8$...

    使用示例:
        hashed = hash_password("mypassword123")
        # 存储 hashed 到数据库
    """
    # 调用_ph.hash方法进行哈希
    # 这个方法会自动生成随机盐，并进行多次迭代计算
    return _ph.hash(raw)


# 定义verify_password函数，用于验证密码是否正确
# raw: str 用户输入的原始密码
# hashed: str 数据库中存储的哈希值
# -> bool 返回True表示密码正确，False表示错误
def verify_password(raw: str, hashed: str) -> bool:
    """
    验证原始密码是否与哈希值匹配

    参数:
        raw: 用户输入的原始密码
        hashed: 数据库中存储的哈希值

    返回:
        True: 密码正确
        False: 密码错误或验证过程出错

    使用示例:
        is_correct = verify_password("mypassword123", db_hash)
        if is_correct:
            # 登录成功
        else:
            # 密码错误
    """
    try:
        # 调用_ph.verify方法验证密码
        # 这个方法会从哈希中提取参数（盐、迭代次数等）
        # 然后对原始密码进行同样的哈希计算，比较结果
        return _ph.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError):
        # 验证失败：密码不匹配或其他验证错误
        # 返回False，不抛出异常，避免泄露信息
        return False

    # 为什么不抛出异常？
    # 1. 安全性：不应该告诉调用者是密码错误还是其他错误
    # 2. 简化调用：调用者只需要知道成功或失败
    # 3. 防止时序攻击：统一的返回时间