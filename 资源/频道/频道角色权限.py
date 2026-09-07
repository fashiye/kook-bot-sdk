'''
KOOK 频道角色权限资源模块：封装频道角色权限(channel-role)的查看/创建/更新/同步/删除 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/channel (频道角色权限相关小节)
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类


class 频道角色权限资源(资源基类):
    """频道角色权限分类资源：对某个频道设置针对角色或用户的权限覆写规则。"""

    async def 获取详情(self, 频道ID: str) -> Any:
        """
        获取频道角色权限详情(含角色/用户两类覆写规则与是否同步分组权限)。
        参数:
            频道ID: 频道 id。
        返回:
            含 permission_overwrites/permission_users/permission_sync 的 data 字典。
        """
        return await self._请求("GET", "/channel-role/index", 查询参数={"channel_id": 频道ID})

    async def 创建(self, 频道ID: str, 覆写对象: str,
                    对象ID: Optional[str] = None) -> Any:
        """
        给频道新增一条角色或用户的权限覆写规则。
        参数:
            频道ID: 频道 id(传分组 id 会同步到其 sync=1 子频道)。
            覆写对象: 规则对象类型，仅可为 "role_id"(角色)或 "user_id"(用户)。
            对象ID: 角色 id 或用户 id(取决于覆写对象)。
        返回:
            含 user_id/role_id、allow、deny 的 data 字典。
        """
        创建数据: dict[str, Any] = {"channel_id": 频道ID, "type": 覆写对象}
        if 对象ID is not None:
            创建数据["value"] = 对象ID
        return await self._请求("POST", "/channel-role/create", 数据=创建数据)

    async def 更新(self, 频道ID: str, 覆写对象: str, 对象ID: str,
                    允许权限: int = 0, 拒绝权限: int = 0) -> Any:
        """
        更新频道上某角色/用户的权限覆写规则。
        参数:
            频道ID: 频道 id(传分组 id 会同步到其 sync=1 子频道)。
            覆写对象: "role_id" 或 "user_id"。
            对象ID: 角色 id 或用户 id。
            允许权限: 允许的权限位掩码值。
            拒绝权限: 拒绝的权限位掩码值。
        返回:
            含 user_id/role_id、allow、deny 的 data 字典。
        """
        return await self._请求("POST", "/channel-role/update",
                                数据={"channel_id": 频道ID, "type": 覆写对象, "value": 对象ID,
                                      "allow": 允许权限, "deny": 拒绝权限})

    async def 同步(self, 频道ID: str) -> Any:
        """
        把分组频道的权限配置同步应用到子频道。
        参数:
            频道ID: 分组频道 id。
        返回:
            同步后的 permission_overwrites/permission_users 的 data 字典。
        """
        return await self._请求("POST", "/channel-role/sync", 数据={"channel_id": 频道ID})

    async def 删除(self, 频道ID: str, 覆写对象: str,
                    对象ID: Optional[str] = None) -> None:
        """
        删除频道上某角色/用户的权限覆写规则。
        参数:
            频道ID: 频道 id(传分组 id 会同步到其 sync=1 子频道)。
            覆写对象: "role_id" 或 "user_id"。
            对象ID: 角色 id 或用户 id。
        返回:
            无返回值。
        """
        删除数据: dict[str, Any] = {"channel_id": 频道ID, "type": 覆写对象}
        if 对象ID is not None:
            删除数据["value"] = 对象ID
        await self._请求("POST", "/channel-role/delete", 数据=删除数据)
