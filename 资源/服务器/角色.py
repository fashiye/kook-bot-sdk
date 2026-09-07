'''
KOOK 服务器角色资源模块：封装服务器角色(guild-role)的增删改查与用户角色授予 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/guild-role
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类


class 服务器角色资源(资源基类):
    """服务器角色分类资源：角色列表/创建/更新/删除及赋予/收回用户角色。"""

    async def 获取列表(self, 服务器ID: str, 页码: int = 1, 页大小: int = 50,
                        合并全部分页: bool = False) -> Any:
        """
        获取服务器角色列表。
        参数:
            服务器ID: 服务器 id。
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items(角色列表) 与 meta 的 data 字典；开启合并全部分页时返回列表。
        """
        固定查询: dict[str, Any] = {"guild_id": 服务器ID}

        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            页查询: dict[str, Any] = dict(固定查询)
            页查询.update({"page": 页, "page_size": 每页})
            return await self._请求("GET", "/guild-role/list", 查询参数=页查询)

        if 合并全部分页:
            return await self._合并分页(取一页)
        查询: dict[str, Any] = dict(固定查询)
        查询.update({"page": 页码, "page_size": 页大小})
        return await self._请求("GET", "/guild-role/list", 查询参数=查询)

    async def 创建(self, 服务器ID: str, 名称: Optional[str] = None) -> Any:
        """
        创建服务器角色。
        参数:
            服务器ID: 服务器 id。
            名称: 角色名称；None 则服务端命名为"新角色"。
        返回:
            新角色字典列表(data 为数组)。
        """
        创建数据: dict[str, Any] = {"guild_id": 服务器ID}
        if 名称 is not None:
            创建数据["name"] = 名称
        return await self._请求("POST", "/guild-role/create", 数据=创建数据)

    async def 更新(self, 服务器ID: str, 角色ID: int, 名称: Optional[str] = None,
                    颜色: Optional[int] = None, 是否置顶显示: Optional[bool] = None,
                    是否可提及: Optional[bool] = None, 权限: Optional[int] = None) -> Any:
        """
        更新服务器角色的外观或权限配置。
        参数:
            服务器ID: 服务器 id。
            角色ID: 目标角色 id。
            名称: 新角色名称。
            颜色: 角色色值 0x000000-0xFFFFFF。
            是否置顶显示: True 让该角色用户在用户列表靠前展示。
            是否可提及: 角色是否可被 @ 提及。
            权限: 权限位掩码整型值(比特位定义见 KOOK 权限文档)。
        返回:
            更新后的角色字典列表(data 为数组)。
        """
        更新数据: dict[str, Any] = {"guild_id": 服务器ID, "role_id": 角色ID}
        if 名称 is not None:
            更新数据["name"] = 名称
        if 颜色 is not None:
            更新数据["color"] = 颜色
        if 是否置顶显示 is not None:
            更新数据["hoist"] = 1 if 是否置顶显示 else 0
        if 是否可提及 is not None:
            更新数据["mentionable"] = 1 if 是否可提及 else 0
        if 权限 is not None:
            更新数据["permissions"] = 权限
        return await self._请求("POST", "/guild-role/update", 数据=更新数据)

    async def 删除(self, 服务器ID: str, 角色ID: int) -> None:
        """
        删除服务器角色。
        参数:
            服务器ID: 服务器 id。
            角色ID: 目标角色 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild-role/delete",
                         数据={"guild_id": 服务器ID, "role_id": 角色ID})

    async def 赋予用户(self, 服务器ID: str, 用户ID: str, 角色ID: int) -> Any:
        """
        把服务器角色赋予指定用户。
        参数:
            服务器ID: 服务器 id。
            用户ID: 目标用户 id。
            角色ID: 服务器角色 id。
        返回:
            含 user_id/guild_id/roles(该用户全部角色 id) 的 data 字典。
        """
        return await self._请求("POST", "/guild-role/grant",
                                数据={"guild_id": 服务器ID, "user_id": 用户ID, "role_id": 角色ID})

    async def 收回用户(self, 服务器ID: str, 用户ID: str, 角色ID: int) -> Any:
        """
        收回指定用户的某个服务器角色。
        参数:
            服务器ID: 服务器 id。
            用户ID: 目标用户 id。
            角色ID: 要收回的服务器角色 id。
        返回:
            含 user_id/guild_id/roles(剩余角色 id) 的 data 字典。
        """
        return await self._请求("POST", "/guild-role/revoke",
                                数据={"guild_id": 服务器ID, "user_id": 用户ID, "role_id": 角色ID})
