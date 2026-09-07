'''
KOOK 频道资源模块：封装服务器频道(channel)的增删改查与语音频道成员操作 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/channel
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类
from ...模型.类型 import 频道类型                          # 频道类型枚举(分组/文字/语音)


class 频道资源(资源基类):
    """频道分类资源：管理服务器内文字/语音/分组频道。"""

    async def 获取列表(self, 服务器ID: str, 类型: Optional[频道类型 | int] = None,
                        父频道ID: Optional[str] = None,
                        页码: int = 1, 页大小: int = 50, 合并全部分页: bool = False) -> Any:
        """
        获取服务器内频道列表。
        参数:
            服务器ID: 服务器 id。
            类型: 频道类型过滤(分组0/文字1/语音2)，None 返回全部。
            父频道ID: 限定某分组下的子频道。
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items(频道列表) 与 meta 的 data 字典；开启合并全部分页时返回列表。
        """
        固定查询: dict[str, Any] = {"guild_id": 服务器ID}
        if 类型 is not None:
            固定查询["type"] = int(类型)
        if 父频道ID:
            固定查询["parent_id"] = 父频道ID

        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            页查询: dict[str, Any] = dict(固定查询)
            页查询.update({"page": 页, "page_size": 每页})
            return await self._请求("GET", "/channel/list", 查询参数=页查询)

        if 合并全部分页:
            return await self._合并分页(取一页)
        查询: dict[str, Any] = dict(固定查询)
        查询.update({"page": 页码, "page_size": 页大小})
        return await self._请求("GET", "/channel/list", 查询参数=查询)

    async def 获取详情(self, 频道ID: str, 需要子频道: bool = False) -> Any:
        """
        获取频道详情。
        参数:
            频道ID: 频道 id。
            需要子频道: True 时返回子频道 id 列表(用于分组频道)。
        返回:
            频道信息字典。
        """
        return await self._请求("GET", "/channel/view",
                                查询参数={"target_id": 频道ID, "need_children": 需要子频道})

    async def 创建(self, 服务器ID: str, 名称: str,
                    类型: 频道类型 | int = 频道类型.文字,
                    父频道ID: Optional[str] = None, 人数上限: int = 0,
                    音质: str = "2", 是分组: bool = False) -> Any:
        """
        创建服务器频道(文字/语音/分组)。
        参数:
            服务器ID: 服务器 id。
            名称: 频道名称。
            类型: 频道类型，默认文字频道。
            父频道ID: 父分组频道 id，可选。
            人数上限: 语音频道人数上限，最大 99，0 表示默认。
            音质: 语音音质，1 流畅/2 正常/3 高质量。
            是分组: 是否创建分组频道；为真时其余参数无效(只传三个字段)。
        返回:
            新频道信息字典(含 id)。
        """
        if 是分组:
            # 分组频道只接收三个字段，其余一律不传
            创建数据: dict[str, Any] = {"guild_id": 服务器ID, "name": 名称, "is_category": 1}
        else:
            创建数据 = {"guild_id": 服务器ID, "name": 名称, "type": int(类型),
                        "limit_amount": 人数上限, "voice_quality": 音质}
            if 父频道ID:
                创建数据["parent_id"] = 父频道ID
        return await self._请求("POST", "/channel/create", 数据=创建数据)

    async def 更新(self, 频道ID: str, 名称: Optional[str] = None,
                    排序: Optional[int] = None, 父频道ID: Optional[str] = None,
                    频道简介: Optional[str] = None, 慢速模式毫秒: Optional[int] = None,
                    人数上限: Optional[int] = None, 音质: Optional[str] = None,
                    密码: Optional[str] = None) -> Any:
        """
        编辑频道(按需传参，None 字段保持不变)。
        参数:
            频道ID: 目标频道 id。
            名称: 新频道名称。
            排序: 频道排序值(越小越靠前)。
            父频道ID: 移入的新分组 id；传 "0" 代表移出分组。
            频道简介: 文字频道简介。
            慢速模式毫秒: 文字频道发言间隔(仅支持官方枚举值：0/5000/10000/15000/30000/60000/120000/300000/600000/900000/1800000/3600000/7200000/21600000)。
            人数上限: 语音频道容量，最大 99。
            音质: 语音音质，1 流畅/2 正常/3 高质量。
            密码: 语音频道进入密码。
        返回:
            更新后的频道信息字典。
        """
        更新数据: dict[str, Any] = {"channel_id": 频道ID}
        if 名称 is not None:
            更新数据["name"] = 名称
        if 排序 is not None:
            更新数据["level"] = 排序
        if 父频道ID is not None:
            更新数据["parent_id"] = 父频道ID
        if 频道简介 is not None:
            更新数据["topic"] = 频道简介
        if 慢速模式毫秒 is not None:
            更新数据["slow_mode"] = 慢速模式毫秒
        if 人数上限 is not None:
            更新数据["limit_amount"] = 人数上限
        if 音质 is not None:
            更新数据["voice_quality"] = 音质
        if 密码 is not None:
            更新数据["password"] = 密码
        return await self._请求("POST", "/channel/update", 数据=更新数据)

    async def 删除(self, 频道ID: str) -> None:
        """
        删除频道(机器人需具备对应权限)。
        参数:
            频道ID: 待删除频道 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/channel/delete", 数据={"channel_id": 频道ID})

    async def 语音用户列表(self, 频道ID: str) -> Any:
        """
        获取语音频道中当前在线的用户列表。
        参数:
            频道ID: 语音频道 id。
        返回:
            用户字典列表。
        """
        return await self._请求("GET", "/channel/user-list", 查询参数={"channel_id": 频道ID})

    async def 移动语音用户(self, 目标频道ID: str, 用户ID列表: list[str]) -> None:
        """
        把若干在线用户移动到另一个语音频道。
        参数:
            目标频道ID: 目标语音频道 id。
            用户ID列表: 待移动用户 id 数组(须在当前语音频道在线)。
        返回:
            无返回值。
        """
        await self._请求("POST", "/channel/move-user",
                         数据={"target_id": 目标频道ID, "user_ids": 用户ID列表})

    async def 踢出语音用户(self, 频道ID: str, 用户ID: str) -> None:
        """
        把用户踢出语音频道(机器人需具备移动成员权限)。
        参数:
            频道ID: 语音频道 id。
            用户ID: 待踢出用户 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/channel/kickout",
                         数据={"channel_id": 频道ID, "user_id": 用户ID})
