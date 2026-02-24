# 1.1 app/core/http_consts.py
# HTTP相关常量配置
#
# 这个文件存放所有和HTTP请求/响应相关的常量名字。
# 把字符串集中写在这里，其他地方直接引用变量名，能避免手抖写错字母。


# ========== HTTP头字段 ==========
# 这些是放在请求/响应头里的标识，用来传递额外的信息

# 定义一个常量，名字是HDR_REQUEST_ID，值是字符串"X-Request-Id"
# HDR是"Header"（HTTP头）的缩写
# REQUEST_ID表示这是请求ID相关的头
# 等号右边是具体的HTTP头字段名，遵循HTTP协议规范，X-前缀表示是自定义头
HDR_REQUEST_ID = "X-Request-Id"

# 定义一个常量，名字是HDR_RESPONSE_TIME_MS，值是字符串"X-Response-Time-Ms"
# RESPONSE_TIME表示响应时间，MS是毫秒的缩写
# 这个头用来告诉客户端服务器处理这个请求花了多少毫秒
HDR_RESPONSE_TIME_MS = "X-Response-Time-Ms"

# 定义一个常量，名字是HDR_CACHE_CONTROL，值是字符串"Cache-Control"
# CACHE_CONTROL是HTTP标准头，不是自定义的，所以没有X-前缀
# 这个头用来控制浏览器或CDN等缓存服务器的缓存行为
HDR_CACHE_CONTROL = "Cache-Control"


# ========== 应用内部状态 ==========
# 这是在程序内部存数据用的键名

# 定义一个常量，名字是STATE_REQUEST_ID，值是字符串"request_id"
# STATE表示这是应用状态（application state）中用的键
# REQUEST_ID表示这是存储请求ID用的键名
# 这个键用来在应用程序内部状态中存储和传递请求ID
# 比如在FastAPI中可以通过request.state.request_id访问
STATE_REQUEST_ID = "request_id"