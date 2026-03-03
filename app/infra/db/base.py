# 2.1 app/infra/db/base.py
# 数据库模型基类模块
#
# 这个文件定义了所有数据库模型类的基类。
# 使用SQLAlchemy的DeclarativeBase作为基类，可以让所有模型类继承统一的基类，
# 方便后续添加通用的列（如创建时间、更新时间）或通用的方法。

# 从sqlalchemy.orm模块导入DeclarativeBase类
# sqlalchemy是Python中最流行的ORM（对象关系映射）库
# orm是SQLAlchemy中用于对象关系映射的子模块
# DeclarativeBase是SQLAlchemy 2.0中推荐的声明式基类
# 所有数据库模型类都需要继承这个基类才能被SQLAlchemy识别为模型
from sqlalchemy.orm import DeclarativeBase


# 定义Base类，继承自DeclarativeBase
# class是定义类的关键字
# Base是类名，代表所有模型类的基类
# (DeclarativeBase) 表示继承自SQLAlchemy的DeclarativeBase类
# 继承DeclarativeBase后，这个类就获得了ORM的所有基础功能
class Base(DeclarativeBase):
    # pass是Python的关键字，表示这个类暂时没有任何额外的方法或属性
    # 这里使用pass是因为目前只需要继承DeclarativeBase，不需要添加额外功能
    # 后续如果需要给所有模型添加通用字段（如created_at、updated_at），可以在这里添加
    pass