'''
KOOK 接口常量模块：存放 REST 请求公共常量，供请求引擎与各资源模块共享引用，避免模块间循环导入。
'''

# KOOK 开放平台 REST 接口根地址(Bot 与用户接口共用，各接口路径以 / 开头拼接在其后)
接口根地址: str = "https://www.kookapp.cn/api/v3"
