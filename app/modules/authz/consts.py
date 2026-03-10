# 7.1 app/modules/authz/consts.py
# 权限作用域常量定义模块
#
# 这个文件定义了授权模块中使用的作用域常量，用于表示权限生效的范围。
# 例如，global 表示全局范围，适用于所有工作空间或资源，拥有所有权限。

# 从__future__导入annotations功能
# 这行代码的作用是让类型注解在运行时不会被评估，保持为字符串形式
# 这样可以在类型提示中使用尚未定义的类，避免循环引用
from __future__ import annotations

# 从typing模块导入Final，用于定义常量类型
# Final 是类型提示，表示这个变量是常量，不应该被重新赋值
# 它不会在运行时强制常量性，但可以帮助静态类型检查器发现错误
from typing import Final

# 定义全局作用域常量，值为 "global"
# SCOPE_GLOBAL 常量用来表示拥有一切权限，可以访问所有的工作区
# 在权限检查中，如果用户的作用域包含 global，则视为拥有所有权限
SCOPE_GLOBAL: Final[str] = "global"
# global这个常量用来表示拥有一切权限，可以访问所有的工作区