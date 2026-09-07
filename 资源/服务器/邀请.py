'''
KOOK 邀请资源模块：封装服务器/频道邀请链接(invite)的查询/创建/删除 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/invite
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类


class 邀请资源(资源基类):
    """邀请分类资源：管理机器人所在服务器的邀请链接。"""

    async def 获取列表(self, 服务器ID: Optional[str] = None, 频道ID: Optional[str] = None,
                        页码: int = 1, 页大小: int = 50, 合并全部分页: bool = False) -> Any:
        """
        获取服务器或频道的邀请链接列表。
        参数:
            服务器ID: 服务器 id，与 频道ID 至少填一个。
            频道ID: 频道 id。
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items(邀请列表) 与 meta 的 data 字典；开启合并全部分页时返回列表。
        """
        固定查询: dict[str, Any] = {}
        if 服务器ID:
            固定查询["guild_id"] = 服务器ID
        if 频道ID:
            固定查询["channel_id"] = 频道ID

        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            页查询: dict[str, Any] = dict(固定查询)
            页查询.update({"page": 页, "page_size": 每页})
            return await self._请求("GET", "/invite/list", 查询参数=页查询)

        if 合并全部分页:
            return await self._合并分页(取一页)
        查询: dict[str, Any] = dict(固定查询)
        查询.update({"page": 页码, "page_size": 页大小})
        return await self._请求("GET", "/invite/list", 查询参数=查询)

    async def 创建(self, 频道ID: Optional[str] = None, 服务器ID: Optional[str] = None,
                    有效时长秒: int = 604800, 使用次数: int = -1) -> Any:
        """
        创建服务器/频道邀请链接。
        参数:
            频道ID: 目标频道 id，与 服务器ID 至少填一个。
            服务器ID: 目标服务器 id。
            有效时长秒: 有效秒数，可选 0(永不)/1800/3600/21600/43200/86400/604800，默认 7 天。
            使用次数: -1 无限制，或 1/5/10/25/50/100。
        返回:
            data 字典，含 url(如 https://kook.top/xxxx)。
        """
        # 邀请参数，频道与服务器至少其一
        邀请数据: dict[str, Any] = {"duration": 有效时长秒, "setting_times": 使用次数}
        if 频道ID:
            邀请数据["channel_id"] = 频道ID
        if 服务器ID:
            邀请数据["guild_id"] = 服务器ID
        return await self._请求("POST", "/invite/create", 数据=邀请数据)

    async def 删除(self, 邀请码: str, 服务器ID: Optional[str] = None,
                    频道ID: Optional[str] = None) -> None:
        """
        删除邀请链接。
        参数:
            邀请码: 待删除链接的 url_code。
            服务器ID: 可选，链接所在服务器 id。
            频道ID: 可选，链接所在频道 id。
        返回:
            无返回值。
        """
        删除数据: dict[str, Any] = {"url_code": 邀请码}
        if 服务器ID:
            删除数据["guild_id"] = 服务器ID
        if 频道ID:
            删除数据["channel_id"] = 频道ID
        await self._请求("POST", "/invite/delete", 数据=删除数据)
