# 4.7 app/api/middleware/real_ip.py
# 获取客户端真实IP模块
#
# 拿到客户的真实IP，但是客户一旦伪装就很可能拿不到。
# 这个文件提供了从请求中获取客户端真实IP地址的函数。
# 由于代理、负载均衡的存在，直接取request.client.host可能拿到的是代理的IP，
# 所以需要从X-Forwarded-For、X-Real-IP等代理传递的头信息中获取真实IP。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
from __future__ import annotations

# 从fastapi导入Request类，用于获取请求信息
from fastapi import Request


# 定义get_real_ip函数，从请求中获取客户端真实IP
# request: Request 参数，FastAPI请求对象
# -> str | None 返回IP地址字符串或None（如果获取不到）
def get_real_ip(request: Request) -> str | None:
    """
    获取客户端真实IP地址

    优先级：
    1. X-Forwarded-For 头的第一个IP（最原始的客户端IP）
    2. X-Real-IP 头
    3. request.client.host（直接连接的IP）

    注意：这些头信息可以被伪造，所以不能完全信任。
    如果应用部署在可信的代理（如Nginx）后面，可以信任代理设置的这些头。
    """

    # 方法1：从X-Forwarded-For头获取
    # X-Forwarded-For是HTTP标准代理头，格式为：client, proxy1, proxy2
    # 最左边的是最原始的客户端IP，后面是经过的代理IP
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # 用逗号分割字符串，并去掉每个部分的首尾空格
        # 过滤掉空字符串（比如 " , " 这种情况）
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            # 返回第一个IP（最原始的客户端IP）
            return parts[0]

    # 方法2：从X-Real-IP头获取
    # X-Real-IP是Nginx等代理常用的头，直接传递真实IP
    xri = request.headers.get("X-Real-IP")
    if xri and xri.strip():
        # 去掉首尾空格后返回
        return xri.strip()

    # 方法3：直接从请求的client对象获取
    # request.client.host 是FastAPI直接获取的连接IP
    # 如果没有代理，这个就是客户端真实IP
    # 如果有代理，这个就是代理的IP
    if request.client:
        return request.client.host

    # 如果以上都获取不到，返回None
    return None

# 使用场景：
# 1. 审计日志记录操作IP
# 2. 限流功能按IP限流
# 3. 安全功能（如IP黑名单）
#
# 注意：如果应用直接对外暴露（没有代理），直接使用request.client.host即可。
# 如果有代理，需要在代理（如Nginx）上配置正确的头信息传递。