# 2.7 app/infra/celery/celery_app.py
# Celery分布式任务队列应用模块
#
# 这个文件创建并配置Celery应用实例，用于处理异步任务（如发送邮件、生成报表等）。
# Celery是一个分布式任务队列，可以将耗时任务放到后台执行，提高API响应速度。
# 这里配置了消息代理（RabbitMQ）和结果后端（Redis），并设置了序列化方式。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从celery模块导入Celery类
# celery是Python最流行的分布式任务队列库
# Celery类用于创建Celery应用实例，所有任务定义和执行都通过这个实例
from celery import Celery

# 从应用的配置模块导入settings对象
# settings包含了所有应用配置，包括RabbitMQ连接URL和Celery相关配置
from app.core.config import settings

# 创建Celery应用实例
# 变量名celery_app，在项目其他地方导入使用
celery_app = Celery(
    # 第一个参数：Celery应用的名称
    # "enterprise_assistant" 是这个Celery应用的标识符
    # 会在日志、监控中显示，用于区分不同的Celery应用
    "enterprise_assistant",

    # broker: 消息代理的URL
    # Celery使用消息代理来传递任务，这里配置为RabbitMQ
    # 从settings.rabbitmq_url获取，格式如：amqp://user:pass@localhost:5672
    broker=settings.rabbitmq_url,

    # backend: 结果后端的URL
    # 用于存储任务执行的结果，这里配置为Redis
    # 从settings.celery_result_backend获取，格式如：redis://localhost:6379/1
    backend=settings.celery_result_backend,

    # include: 需要导入的任务模块列表
    # 这里是一个空列表，表示暂时没有定义任何任务模块
    # 后续添加任务时，需要在这里加入模块路径，如：["app.tasks.email_tasks"]
    include=[
        # 示例： "app.tasks.email_tasks",
        # 示例： "app.tasks.report_tasks",
    ],
)

# 更新Celery应用的配置
# celery_app.conf 是Celery的配置对象，可以通过update方法批量更新配置
celery_app.conf.update(
    # task_serializer: 任务序列化方式
    # "json" 表示任务参数使用JSON格式序列化
    # JSON是跨语言支持的通用格式，可读性好
    task_serializer="json",

    # accept_content: 接受的内容类型
    # ["json"] 表示只接受JSON格式的序列化内容
    # 限制接受的类型可以提高安全性
    accept_content=["json"],

    # result_serializer: 结果序列化方式
    # "json" 表示任务结果也使用JSON格式序列化
    result_serializer="json",

    # enable_utc: 是否启用UTC时间
    # True 表示所有时间相关操作使用UTC时区
    # 使用UTC可以避免时区问题，便于分布式部署
    enable_utc=True,

    # timezone: 时区设置
    # "UTC" 明确指定使用UTC时区
    timezone="UTC",

    # task_always_eager: 任务是否同步执行（调试用）
    # bool()确保转换为布尔值，从配置中读取
    # 如果为True，任务会在本地立即执行，而不发送到worker
    # 开发测试时常用，生产环境应为False
    task_always_eager=bool(settings.celery_task_always_eager),
)

# 使用示例：
# 在其他文件中定义任务：
# from app.infra.celery.celery_app import celery_app
#
# @celery_app.task
# def send_email(email: str, content: str):
#     # 发送邮件的代码
#     pass
#
# 调用任务：
# send_email.delay("user@example.com", "Hello")