'''
KOOK 帖子资源模块：封装帖子分区(category)与帖子(thread)的发布/评论/查询/删除 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/thread
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ..核心.资源基座 import 资源基类, 整理发送内容         # 资源基类与内容整理工具


class 帖子资源(资源基类):
    """帖子分类资源：管理服务器帖子频道中的分区、帖子与评论。"""

    async def 获取分区列表(self, 频道ID: str) -> Any:
        """
        获取帖子频道的分区列表。
        参数:
            频道ID: 帖子频道 id。
        返回:
            含 list(分区数组) 的 data 字典，分区含 id/name/allow/deny/roles。
        """
        return await self._请求("GET", "/category/list", 查询参数={"channel_id": 频道ID})

    async def 创建(self, 服务器ID: str, 频道ID: str, 标题: str,
                    内容: str | list | dict, 分区ID: Optional[str] = None,
                    封面: Optional[str] = None) -> Any:
        """
        发布一篇帖子。
        参数:
            服务器ID: 帖子所在服务器 id。
            频道ID: 帖子频道 id。
            标题: 帖子标题。
            内容: 正文(文本或卡片结构，规则同频道消息)。
            分区ID: 帖子分区 id；None 进默认综合分区。
            封面: 封面图片 url，可选。
        返回:
            新帖子详情字典(含 id/post_id)。
        """
        # 帖子正文与频道消息一致，卡片结构自动序列化
        _, 内容文本 = 整理发送内容(内容)
        创建数据: dict[str, Any] = {"guild_id": 服务器ID, "channel_id": 频道ID,
                                     "title": 标题, "content": 内容文本}
        if 分区ID:
            创建数据["category_id"] = 分区ID
        if 封面:
            创建数据["cover"] = 封面
        return await self._请求("POST", "/thread/create", 数据=创建数据)

    async def 回复(self, 频道ID: str, 帖子ID: str, 内容: str,
                    回复对象ID: Optional[str] = None) -> Any:
        """
        对帖子发表评论或回复某条评论(楼中楼)。
        参数:
            频道ID: 帖子频道 id。
            帖子ID: 目标帖子 id。
            内容: 评论文本。
            回复对象ID: 回复他人评论时的 post_id；评论主楼则不传。
        返回:
            新评论详情字典。
        """
        回复数据: dict[str, Any] = {"channel_id": 频道ID, "thread_id": 帖子ID, "content": 内容}
        if 回复对象ID:
            回复数据["reply_id"] = 回复对象ID
        return await self._请求("POST", "/thread/reply", 数据=回复数据)

    async def 获取详情(self, 频道ID: str, 帖子ID: str) -> Any:
        """
        获取帖子详情(含主楼内容与统计)。
        参数:
            频道ID: 帖子频道 id。
            帖子ID: 目标帖子 id。
        返回:
            帖子详情字典。
        """
        return await self._请求("GET", "/thread/view",
                                查询参数={"channel_id": 频道ID, "thread_id": 帖子ID})

    async def 获取列表(self, 频道ID: str, 分区ID: Optional[str] = None,
                        排序: Optional[int] = None, 页大小: int = 30,
                        翻页时间: Optional[int] = None) -> Any:
        """
        获取帖子列表。
        参数:
            频道ID: 帖子频道 id。
            分区ID: 帖子分区 id，None 默认综合分区。
            排序: 1 最新回复 / 2 最新创建；None 按频道设置。
            页大小: 单页条数，默认 30。
            翻页时间: 翻页起点时间(取上一页最后一帖对应时间；sort=1 用 latest_active_time，sort=2 用 create_time)。
        返回:
            含 items(帖子列表) 的 data 字典。
        """
        查询: dict[str, Any] = {"channel_id": 频道ID, "page_size": 页大小}
        if 分区ID:
            查询["category_id"] = 分区ID
        if 排序 is not None:
            查询["sort"] = 排序
        if 翻页时间 is not None:
            查询["time"] = 翻页时间
        return await self._请求("GET", "/thread/list", 查询参数=查询)

    async def 删除(self, 频道ID: str, 帖子ID: Optional[str] = None,
                    楼ID: Optional[str] = None) -> None:
        """
        删除帖子或其中的评论/回复。
        参数:
            频道ID: 帖子频道 id。
            帖子ID: 删除整帖时的帖子 id(与 楼ID 同时给则只删对应楼)。
            楼ID: 删除单条评论/回复时的 post_id。
        返回:
            无返回值。
        """
        删除数据: dict[str, Any] = {"channel_id": 频道ID}
        if 帖子ID:
            删除数据["thread_id"] = 帖子ID
        if 楼ID:
            删除数据["post_id"] = 楼ID
        await self._请求("POST", "/thread/delete", 数据=删除数据)

    async def 获取回复列表(self, 频道ID: str, 帖子ID: str, 排序方向: str = "asc",
                            页码: int = 1, 楼ID: Optional[str] = None,
                            翻页时间: Optional[str] = None,
                            页大小: Optional[int] = None) -> Any:
        """
        获取帖子的评论/回复列表(可查看楼中楼)。
        参数:
            频道ID: 帖子频道 id。
            帖子ID: 目标帖子 id。
            排序方向: "asc" 升序或 "desc" 降序。
            页码: 页码。
            楼ID: 某条评论的 post_id，查看其楼中楼时传。
            翻页时间: 某条回复的 create_time，用于分页定位。
            页大小: 单页条数。
        返回:
            含 meta 与 items(评论列表) 的 data 字典。
        """
        查询: dict[str, Any] = {"channel_id": 频道ID, "thread_id": 帖子ID,
                                 "order": 排序方向, "page": 页码}
        if 楼ID:
            查询["post_id"] = 楼ID
        if 翻页时间:
            查询["time"] = 翻页时间
        if 页大小 is not None:
            查询["page_size"] = 页大小
        return await self._请求("GET", "/thread/post", 查询参数=查询)
