# 1.10 app/core/security_defaults.py
# 安全响应头默认值配置模块
#
# 这个文件定义了HTTP安全响应头的默认值。
# 前三个变量都是和HTTP协议密切相关的参数及其取值。
# 这些安全头可以帮助防范常见的Web安全漏洞，如点击劫持、MIME类型嗅探等。

# 定义HSTS（HTTP Strict Transport Security）的默认最大存活时间
# HSTS强制浏览器只能通过HTTPS访问网站，禁止使用HTTP
# 31536000秒 = 1年（365天 * 24小时 * 3600秒）
# 这个值表示告诉浏览器，在接下来的一年内，只能使用HTTPS访问本站
DEFAULT_HSTS_MAX_AGE = 31536000

# 定义X-Frame-Options响应头的默认值
# 这个头用于控制当前页面是否可以被嵌入到frame/iframe中，防止点击劫持攻击
# "DENY" 表示禁止任何域名将本页面嵌入到frame中
# 其他可选值：
#   - "SAMEORIGIN": 只允许同源域名嵌入
#   - "ALLOW-FROM uri": 允许指定URI嵌入（已废弃）
DEFAULT_X_FRAME_OPTIONS = "DENY"

# 定义Referrer-Policy响应头的默认值
# 这个头控制在跳转时是否发送来源信息（referrer）
# "no-referrer" 表示在任何情况下都不发送referrer信息
# 其他可选值：
#   - "no-referrer-when-downgrade": 从HTTPS到HTTP时不发送（默认）
#   - "same-origin": 同源才发送
#   - "strict-origin-when-cross-origin": 跨域只发送源信息
DEFAULT_REFERRER_POLICY = "no-referrer"

# 定义Permissions-Policy响应头的默认值
# 这个头用于控制浏览器是否允许网页使用某些敏感功能
# 这里控制浏览器是否允许地理位置、麦克风和摄像头
# "geolocation=(), microphone=(), camera=()" 表示禁止所有来源使用这些功能
# 括号内可以指定允许的来源，如：
#   - "geolocation=(self)" 只允许同源使用
#   - "geolocation=(self 'https://example.com')" 允许同源和指定域名
# 默认禁止这些敏感权限，可以提高网站安全性
DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=()"