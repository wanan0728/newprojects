# 6.3 app/modules/authn/service.py
# 认证模块核心服务
#
# 这个文件提供了刷新令牌（refresh token）的生成、存储、验证等核心功能。
# 刷新令牌用于在访问令牌过期后获取新的访问令牌，同时支持令牌吊销机制。
# 使用Redis存储刷新令牌信息，通过Lua脚本保证原子性操作。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 导入hashlib模块，用于计算SHA256哈希
import hashlib
# 导入re模块，用于正则表达式验证
import re
# 导入secrets模块，用于生成安全的随机字符串
import secrets
# 导入uuid模块，用于生成唯一的RID
import uuid
# 从dataclasses导入dataclass装饰器，用于定义数据类
from dataclasses import dataclass
# 从datetime导入timedelta，用于计算过期时间
from datetime import timedelta

# 导入认证模块常量
from app.modules.authn.consts import (
    MAX_REFRESH_TOKEN_LEN,  # 刷新令牌最大长度
    MAX_RID_LEN,  # RID段最大长度
    MAX_SECRET_LEN,  # SECRET段最大长度
    REDIS_PREFIX_REFRESH,  # 刷新令牌Redis键前缀
    REDIS_PREFIX_TOKENVER,  # 令牌版本Redis键前缀
    REFRESH_SEPARATOR,  # 刷新令牌分隔符
)


# 定义RefreshTokenPair数据类，表示刷新令牌拆分后的结构
# frozen=True 表示实例不可变（只读）
@dataclass(frozen=True)
class RefreshTokenPair:
    """
    refresh token拆分后的结构

    属性:
        rid: 用于redis key的随机uuid，作为令牌标识
        secret: 用于验证的随机密钥，这里只存哈希，不存明文
    """
    rid: str  # 用于redis key的随机uuid
    secret: str  # 用于验证的随机密钥，这里只存哈希，不存明文


# 编译正则表达式，用于验证UUID格式
# 格式：8-4-4-4-12 的十六进制字符串
_RE_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# 编译正则表达式，定义secret允许的字符集合
# 允许字母、数字、点、下划线、波浪线、短横线
_RE_SAFE_SEG = re.compile(r"^[A-Za-z0-9._~-]+$")  # secret允许的字符集合


# 定义_sha256函数，计算字符串的SHA256哈希值（十六进制）
# s: str 输入字符串
# -> str 返回哈希值的十六进制表示
def _sha256(s: str) -> str:
    """计算sha256 hex，用于存储secret的哈希"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# 定义mint_refresh_token函数，生成一个新的刷新令牌
# -> RefreshTokenPair 返回令牌对（rid + secret）
def mint_refresh_token() -> RefreshTokenPair:
    """生成一个新未入库的refresh token"""
    return RefreshTokenPair(
        rid=str(uuid.uuid4()),  # 生成UUID作为RID
        secret=secrets.token_urlsafe(48)  # 生成48字节的URL安全随机字符串作为secret
    )


# 定义pack_refresh函数，将令牌对打包成字符串
# pair: RefreshTokenPair 令牌对
# -> str 返回给客户端的刷新令牌字符串
def pack_refresh(pair: RefreshTokenPair) -> str:
    """把rid和secret拼成refresh_token字符串给客户端保存"""
    return f"{pair.rid}{REFRESH_SEPARATOR}{pair.secret}"


# 定义unpack_refresh函数，从客户端传入的令牌解析出令牌对
# token: str 客户端传入的刷新令牌字符串
# -> RefreshTokenPair 返回解析后的令牌对
def unpack_refresh(token: str) -> RefreshTokenPair:
    """从客户端传入的refresh_token解析出rid+secret并做严格校验"""
    # 检查是否为字符串
    if not isinstance(token, str):
        raise ValueError("bad_refresh_format")

    # 检查长度是否在允许范围内
    if len(token) == 0 or len(token) > int(MAX_REFRESH_TOKEN_LEN):
        raise ValueError("bad_refresh_format")

    # 检查是否包含分隔符
    if REFRESH_SEPARATOR not in token:
        raise ValueError("bad_refresh_format")

    # 用分隔符分割，只分割第一个
    rid, secret = token.split(REFRESH_SEPARATOR, 1)  # 将传入的refresh token从中间的圆点拆开
    rid = rid.strip()  # 去掉RID首尾空格
    secret = secret.strip()  # 去掉SECRET首尾空格

    # 检查RID和SECRET是否为空
    if not rid or not secret:
        raise ValueError("bad_refresh_format")

    # 检查长度是否超过最大限制
    if len(rid) > int(MAX_RID_LEN) or len(secret) > int(MAX_SECRET_LEN):
        raise ValueError("bad_refresh_format")

    # 检查RID是否为有效的UUID格式
    if not _RE_UUID.match(rid):
        raise ValueError("bad_refresh_format")

    # 检查SECRET是否只包含允许的字符
    if not _RE_SAFE_SEG.match(secret):
        raise ValueError("bad_refresh_format")

    # 返回解析后的令牌对
    return RefreshTokenPair(rid=rid, secret=secret)


# 定义key_refresh函数，生成刷新令牌在Redis中的键名
# rid: str 令牌的RID
# -> str 返回完整的Redis键名
def key_refresh(rid: str) -> str:
    """redis中refresh token的key"""
    return f"{REDIS_PREFIX_REFRESH}{rid}"


# 定义key_tokenver函数，生成令牌版本在Redis中的键名
# user_id: int 用户ID
# -> str 返回完整的Redis键名
def key_tokenver(user_id: int) -> str:
    """redis中tokenver的key"""
    return f"{REDIS_PREFIX_TOKENVER}{int(user_id)}"


# 定义_decode_bytes辅助函数，处理Redis可能返回的字节数据
# v: Redis返回的值
# -> 解码后的字符串或原值
def _decode_bytes(v):
    """redis客户端可能返回bytes，这里做统一解码"""
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8")
        except Exception:
            return None
    return v


# 定义get_tokenver异步函数，获取用户的当前令牌版本
# redis: Redis客户端
# user_id: int 用户ID
# -> int 返回令牌版本，不存在则返回0
async def get_tokenver(redis, user_id: int) -> int:
    """获取某用户当前token version。不存在则0"""
    # 从Redis获取令牌版本
    v = await redis.get(key_tokenver(int(user_id)))
    v = _decode_bytes(v)  # 解码字节数据
    if v is None:
        return 0
    try:
        return int(v)  # 转换为整数
    except Exception:
        return 0


# 定义bump_tokenver异步函数，增加用户的令牌版本
# redis: Redis客户端
# user_id: int 用户ID
# -> int 返回新的令牌版本
async def bump_tokenver(redis, user_id: int) -> int:
    """tokenver自增，这里要踢掉所有旧access token"""
    # incr命令原子性地增加计数，返回新值
    return int(await redis.incr(key_tokenver(int(user_id))))


# 定义store_refresh异步函数，将刷新令牌存储到Redis
# redis: Redis客户端
# pair: RefreshTokenPair 令牌对
# user_id: int 用户ID
# token_ver: int 当前令牌版本
# ttl_days: int 过期天数
# -> None 无返回值
async def store_refresh(
        redis,
        *,
        pair: RefreshTokenPair,
        user_id: int,
        token_ver: int,
        ttl_days: int,
) -> None:
    """把refresh token存到 redis，并设置TTL"""
    # 构建存储值：用户ID|令牌版本|secret哈希
    val = f"{int(user_id)}|{int(token_ver)}|{_sha256(pair.secret)}"

    # 存储到Redis，设置过期时间
    await redis.set(
        key_refresh(pair.rid),  # Redis键
        val.encode("utf-8"),  # 值（转为字节）
        ex=int(timedelta(days=int(ttl_days)).total_seconds()),  # 过期时间（秒）
    )


# 定义revoke_refresh异步函数，撤销刷新令牌
# redis: Redis客户端
# rid: str 令牌的RID
# -> None 无返回值
async def revoke_refresh(redis, rid: str) -> None:
    """撤销某个refresh，即删除redis key"""
    await redis.delete(key_refresh(rid))


# 定义Lua脚本，用于原子性地验证并消费刷新令牌
# LUA脚本，这里验证一个刷新令牌是否合理，如果合理就消费refresh(消费就是删掉)
# LUA脚本在这里是希望一次性验证并消费，中间不要出现什么问题，不要用了又删不掉
_LUA_VERIFY_AND_CONSUME = """
-- KEYS[1]: Redis键名
-- ARGV[1]: 期望的secret哈希值

local key = KEYS[1]
local want = ARGV[1]

-- 获取存储的值
local v = redis.call("GET", key)
if not v then
  return nil
end

-- 解析存储的值：用户ID|令牌版本|secret哈希
local user_id, token_ver, secret_hash = string.match(v, "^(%d+)%|(%d+)%|(.+)$")
if not user_id then
  return nil
end

-- 验证secret哈希是否匹配
if secret_hash ~= want then
  return nil
end

-- 验证通过，删除该键（消费）
redis.call("DEL", key)
-- 返回用户ID和令牌版本
return {user_id, token_ver}
"""


# 定义verify_and_consume_refresh异步函数，验证并消费刷新令牌
# redis: Redis客户端
# pair: RefreshTokenPair 令牌对
# -> tuple[int, int] | None 返回(用户ID, 令牌版本)或None
async def verify_and_consume_refresh(redis, *, pair: RefreshTokenPair) -> tuple[int, int] | None:
    """校验refresh token并消费掉"""
    # 计算期望的secret哈希
    want_hash = _sha256(pair.secret)

    # 执行Lua脚本
    # eval参数：脚本内容，键数量，键1，参数1
    res = await redis.eval(_LUA_VERIFY_AND_CONSUME, 1, key_refresh(pair.rid), want_hash)

    # 检查返回结果是否为有效的列表/元组
    if not isinstance(res, (list, tuple)) or len(res) != 2:
        return None

    # 解码返回的用户ID和令牌版本
    user_id = _decode_bytes(res[0])
    token_ver = _decode_bytes(res[1])

    try:
        # 转换为整数并返回
        return (int(user_id), int(token_ver))
    except Exception:
        return None