'''
KOOK REST 资源基类模块：所有分类资源对象(频道消息/服务器/用户等)的公共基类与内容整理工具。
各资源类只做"拼参数、调接口"的轻量封装，复用本模块的底层请求委托与发送内容整理，避免重复代码。
'''
from typing import Any, Awaitable, Callable, Optional     # 提供类型注解与回调类型

from ..模型.类型 import 消息类型               # 消息类型枚举，用于自动推断卡片消息类型
import json                                # 提供 JSON 序列化，用于把卡片对象转为消息 content 字符串


def 整理发送内容(内容: str | list | dict, 显式类型: Optional[int] = None) -> tuple[int, str]:
    """
    把要发送的消息内容整理为(消息类型, content字符串)。供频道消息/私信消息等资源复用。
    参数:
        内容: 文本字符串，或卡片 JSON 数组/字典。
        显式类型: 调用方显式指定的消息类型，None 则自动推断。
    返回:
        二元组：消息类型整型值、序列化后的内容字符串。
    """
    if isinstance(内容, (list, dict)):
        # 调用库函数：把卡片结构序列化为 JSON 文本
        # 传入：obj=卡片数组/字典，ensure_ascii=False(保留中文原样输出)
        # 作用：把卡片对象转为 KOOK 发送接口要求的 content JSON 字符串
        # 传出：str 类型的 JSON 文本
        return 消息类型.卡片.value, json.dumps(内容, ensure_ascii=False)
    return (显式类型 if 显式类型 is not None else 消息类型.KMD文本.value), str(内容)


class 资源基类:
    """REST 分类资源的公共基类：持有底层客户端，所有接口方法经 _请求() 统一转发。"""

    def __init__(self, 客户端: "HTTP引擎"):
        """
        绑定底层客户端。
        参数:
            客户端: 已构造的 HTTP 引擎实例(Bot 或用户鉴权)，资源本身不持有连接，只做请求转发。
        """
        self._客户端 = 客户端

    async def _请求(self, 方法: str, 接口路径: str,
                    查询参数: Optional[dict[str, Any]] = None,
                    数据: Optional[dict[str, Any]] = None) -> Any:
        """
        把 REST 请求转发给底层客户端统一执行(鉴权、超时、错误码处理都集中在客户端)。
        参数:
            方法: HTTP 方法(GET/POST)。
            接口路径: 接口路径，如 "/message/create"。
            查询参数: URL 查询参数，GET 请求使用。
            数据: 请求体字典，POST 请求使用。
        返回:
            KOOK 响应的 data 字段，具体结构随接口而定。
        """
        # 调用库方法：委托底层客户端发送请求
        # 传入：方法/路径/查询参数/请求体均原样透传
        # 作用：让所有资源共用同一套鉴权与错误处理
        # 传出：KOOK 响应 data 字段
        return await self._客户端.请求(方法, 接口路径, 查询参数=查询参数, 数据=数据)

    async def _上传文件(self, 接口路径: str, 文件字段名: str,
                         文件字节: bytes, 文件名: str,
                         附加字段: Optional[dict[str, Any]] = None) -> Any:
        """
        把 multipart 文件上传委托给底层客户端统一处理(素材/服务器表情等接口复用)。
        参数:
            接口路径: 接口路径，如 "/asset/create"。
            文件字段名: 表单中文件字段名(如 asset 为 "file"，表情为 "emoji")。
            文件字节: 文件二进制内容。
            文件名: 上传时展示的文件名(需带扩展名以判定类型)。
            附加字段: 额外的普通表单字段，可选。
        返回:
            KOOK 响应的 data 字段。
        """
        # 调用库方法：委托底层客户端发送 multipart 请求
        # 传入：路径/文件字段/字节/文件名/附加字段均透传
        # 作用：让上传类资源复用统一的会话与错误处理
        # 传出：KOOK 响应 data 字段
        return await self._客户端.上传文件(接口路径, 文件字段名, 文件字节, 文件名, 附加字段)

    async def _合并分页(self, 获取一页: Callable[[int, int], Awaitable[dict[str, Any]]],
                         起始页码: int = 1, 页大小: int = 50) -> list[dict[str, Any]]:
        """
        把标准分页接口(返回 items + meta.page_total)的列表自动翻页拉全并合并。
        供各分类资源列表方法的"合并全部分页"选项复用。
        参数:
            获取一页: 异步回调，入参(页码, 每页条数)，返回该页 data 字典(含 items/meta)。
            起始页码: 从第几页开始，默认 1。
            页大小: 每页条数，默认 50。
        返回:
            合并后的全量 items 列表。
        """
        收集结果: list[dict[str, Any]] = []
        页码: int = 起始页码
        while True:
            # 调用回调：请求当前页
            页数据: dict[str, Any] = await 获取一页(页码, 页大小)
            # 页元信息(标准分页才有 page_total)，无元信息则视为单页
            页元信息: dict[str, Any] = 页数据.get("meta", {}) if isinstance(页数据, dict) else {}
            页总计: int = int(页元信息.get("page_total", 1) or 1)
            # 当前页的条目，兼容 items 字段或直接数组
            当页条目: list[dict[str, Any]] = 页数据.get("items", []) if isinstance(页数据, dict) else 页数据
            if isinstance(当页条目, list):
                收集结果.extend(当页条目)
            # 已翻到最后一页或空页则结束
            if not 当页条目 or 页码 >= 页总计:
                break
            页码 += 1
        return 收集结果
