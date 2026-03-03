# 2.6 app/infra/elasticsearch_client.py
# Elasticsearch客户端创建模块
#
# 这个文件负责创建Elasticsearch异步客户端。
# Elasticsearch是一个分布式搜索和分析引擎，用于全文搜索、日志分析等场景。
# 这里根据配置动态创建客户端，支持认证和证书验证配置。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样就可以在类型提示中使用还没定义的类型
from __future__ import annotations

# 从elasticsearch模块导入AsyncElasticsearch类
# elasticsearch是Elasticsearch官方提供的Python客户端库
# AsyncElasticsearch是异步版本的客户端，支持async/await语法
# 使用异步客户端可以避免阻塞事件循环，提高并发处理能力
from elasticsearch import AsyncElasticsearch

# 从应用的配置模块导入settings对象
# settings包含了所有应用配置，包括Elasticsearch的连接信息
# 如：ELASTICSEARCH_URL、ELASTICSEARCH_USERNAME等
from app.core.config import settings


# 定义create_es_client函数，用于创建并返回Elasticsearch异步客户端
# -> AsyncElasticsearch: 类型注解，表示这个函数返回一个AsyncElasticsearch对象
def create_es_client() -> AsyncElasticsearch:
    # 初始化认证信息为None
    # auth变量用于存储认证元组 (username, password)
    auth = None

    # 检查用户名和密码是否都已配置
    # (settings.elasticsearch_username or "").strip() 处理None值，去掉空格
    # 如果用户名和密码都存在（不是空字符串），才启用认证
    if (settings.elasticsearch_username or "").strip() and (settings.elasticsearch_password or "").strip():
        # 创建认证元组，格式为 (username, password)
        # Elasticsearch客户端支持basic_auth参数接收这种格式
        auth = (settings.elasticsearch_username, settings.elasticsearch_password)

    # 创建并返回AsyncElasticsearch客户端实例
    return AsyncElasticsearch(
        # hosts: Elasticsearch服务器地址列表
        # 这里只配置了一个地址，用列表包起来
        # 格式如：["http://localhost:9200"] 或 ["https://es.example.com:9200"]
        hosts=[settings.elasticsearch_url],

        # basic_auth: 基本认证信息
        # 如果auth为None，则不启用认证
        # 如果auth有值，则在请求时自动添加Authorization头
        basic_auth=auth,

        # verify_certs: 是否验证SSL证书
        # bool()确保转换为布尔值，处理可能的字符串"true"/"false"
        # 从配置读取，默认是False（开发环境常用）
        # 在生产环境应该设置为True并配置正确的证书
        verify_certs=bool(settings.elasticsearch_verify_certs),
    )

    # 这个客户端创建后，可以在应用启动时调用：
    # es_client = create_es_client()
    # 然后存储到app.state中供依赖项使用

    # 使用示例：
    # async def search_docs(es: AsyncElasticsearch = Depends(get_es)):
    #     result = await es.search(index="my_index", body={"query": {...}})