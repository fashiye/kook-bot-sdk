'''
KOOK 服务器资源模块：封装服务器(guild)、服务器静音(guild-mute)与服务器助力历史(guild-boost) REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/guild
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类
from ...模型.类型 import 静音类型                          # 静音类型枚举(麦克风闭麦/耳机静音)


class 服务器资源(资源基类):
    """服务器分类资源：查询/管理机器人加入的服务器及其成员静音状态。"""

    async def 获取列表(self, 页码: int = 1, 页大小: int = 50,
                        合并全部分页: bool = False) -> Any:
        """
        获取机器人已加入的服务器列表。
        参数:
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items(服务器列表) 与 meta(分页信息) 的 data 字典；开启合并全部分页时返回列表。
        """
        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            return await self._请求("GET", "/guild/list",
                                    查询参数={"page": 页, "page_size": 每页})

        if 合并全部分页:
            return await self._合并分页(取一页)
        return await self._请求("GET", "/guild/list",
                                查询参数={"page": 页码, "page_size": 页大小})

    async def 获取详情(self, 服务器ID: str) -> Any:
        """
        获取服务器详情(含角色与频道列表)。
        参数:
            服务器ID: 服务器 id。
        返回:
            服务器信息字典。
        """
        return await self._请求("GET", "/guild/view", 查询参数={"guild_id": 服务器ID})

    async def 获取用户列表(self, 服务器ID: str, 频道ID: Optional[str] = None,
                            关键字: Optional[str] = None, 角色ID: Optional[int] = None,
                            手机认证: Optional[bool] = None,
                            活跃时间倒序: Optional[bool] = None,
                            加入时间倒序: Optional[bool] = None,
                            指定用户ID: Optional[str] = None,
                            页码: int = 1, 页大小: int = 50, 合并全部分页: bool = False) -> Any:
        """
        获取服务器中的用户列表(支持按频道/角色/关键字过滤)。
        参数:
            服务器ID: 服务器 id。
            频道ID: 限定该频道内用户，可选。
            关键字: 在用户名或昵称中搜索。
            角色ID: 只取拥有该角色的用户。
            手机认证: True 只取已手机认证，False 只取未认证，None 不限。
            活跃时间倒序: True 按活跃时间倒序；False 顺序；None 不排。
            加入时间倒序: True 按加入时间倒序；False 顺序；None 不排。
            指定用户ID: 只取该用户的信息。
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items/meta/user_count/online_count/offline_count 的 data 字典；开启合并全部分页时返回列表。
        """
        固定查询: dict[str, Any] = {"guild_id": 服务器ID}
        if 频道ID:
            固定查询["channel_id"] = 频道ID
        if 关键字:
            固定查询["search"] = 关键字
        if 角色ID is not None:
            固定查询["role_id"] = 角色ID
        if 手机认证 is not None:
            固定查询["mobile_verified"] = 1 if 手机认证 else 0
        if 活跃时间倒序 is not None:
            固定查询["active_time"] = 1 if 活跃时间倒序 else 0
        if 加入时间倒序 is not None:
            固定查询["joined_at"] = 1 if 加入时间倒序 else 0
        if 指定用户ID:
            固定查询["filter_user_id"] = 指定用户ID

        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            页查询: dict[str, Any] = dict(固定查询)
            页查询.update({"page": 页, "page_size": 每页})
            return await self._请求("GET", "/guild/user-list", 查询参数=页查询)

        if 合并全部分页:
            return await self._合并分页(取一页)
        查询: dict[str, Any] = dict(固定查询)
        查询.update({"page": 页码, "page_size": 页大小})
        return await self._请求("GET", "/guild/user-list", 查询参数=查询)

    async def 修改昵称(self, 服务器ID: str, 昵称: Optional[str] = None,
                       用户ID: Optional[str] = None) -> None:
        """
        修改用户在服务器内的昵称。
        参数:
            服务器ID: 服务器 id。
            昵称: 新昵称(2-64 长度)；None 代表清空昵称。
            用户ID: 目标用户 id；None 修改机器人自己的昵称。
        返回:
            无返回值。
        """
        修改数据: dict[str, Any] = {"guild_id": 服务器ID}
        if 昵称 is not None:
            修改数据["nickname"] = 昵称
        if 用户ID:
            修改数据["user_id"] = 用户ID
        await self._请求("POST", "/guild/nickname", 数据=修改数据)

    async def 离开(self, 服务器ID: str) -> None:
        """
        让机器人离开指定服务器。
        参数:
            服务器ID: 服务器 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild/leave", 数据={"guild_id": 服务器ID})

    async def 踢出(self, 服务器ID: str, 目标用户ID: str) -> None:
        """
        把用户踢出服务器(机器人需具备踢出成员权限)。
        参数:
            服务器ID: 服务器 id。
            目标用户ID: 被踢用户 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild/kickout",
                         数据={"guild_id": 服务器ID, "target_id": 目标用户ID})

    async def 静音列表(self, 服务器ID: str) -> Any:
        """
        获取服务器当前被静音/闭麦的用户列表。
        参数:
            服务器ID: 服务器 id。
        返回:
            含 mic(type=1 闭麦) 与 headset(type=2 静音) 两组用户 id 列表的 data 字典。
        """
        return await self._请求("GET", "/guild-mute/list",
                                查询参数={"guild_id": 服务器ID, "return_type": "detail"})

    async def 添加静音(self, 服务器ID: str, 用户ID: str,
                        静音方式: 静音类型 | int = 静音类型.耳机静音) -> None:
        """
        在服务器内静音/闭麦用户(需具备管理权限)。
        参数:
            服务器ID: 服务器 id。
            用户ID: 目标用户 id。
            静音方式: 1 麦克风闭麦 / 2 耳机静音。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild-mute/create",
                         数据={"guild_id": 服务器ID, "user_id": 用户ID, "type": int(静音方式)})

    async def 删除静音(self, 服务器ID: str, 用户ID: str,
                        静音方式: 静音类型 | int = 静音类型.耳机静音) -> None:
        """
        取消服务器内对用户的静音/闭麦。
        参数:
            服务器ID: 服务器 id。
            用户ID: 目标用户 id。
            静音方式: 1 麦克风闭麦 / 2 耳机静音，需与添加时一致。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild-mute/delete",
                         数据={"guild_id": 服务器ID, "user_id": 用户ID, "type": int(静音方式)})

    async def 助力历史(self, 服务器ID: str, 开始时间: Optional[int] = None,
                        结束时间: Optional[int] = None) -> Any:
        """
        查询服务器的助力包历史(需服务器管理权限)。
        参数:
            服务器ID: 服务器 id。
            开始时间: Unix 秒级时间戳，时间范围起点，可选。
            结束时间: Unix 秒级时间戳，时间范围终点，可选。
        返回:
            按 start_time 倒序的标准分页 data，items 含助力用户与起止时间。
        """
        查询: dict[str, Any] = {"guild_id": 服务器ID}
        if 开始时间 is not None:
            查询["start_time"] = 开始时间
        if 结束时间 is not None:
            查询["end_time"] = 结束时间
        return await self._请求("GET", "/guild-boost/history", 查询参数=查询)
