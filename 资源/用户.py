'''
KOOK 用户资源模块：封装机器人自身与目标用户的用户信息、上下线与在线状态 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/user
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ..核心.资源基座 import 资源基类                       # 资源基类


class 用户资源(资源基类):
    """用户分类资源：以机器人身份查询用户信息并管理机器人自身在线状态。"""

    async def 获取自身信息(self) -> Any:
        """
        获取机器人自身的用户信息。
        返回:
            用户信息字典。
        """
        return await self._请求("GET", "/user/me")

    async def 获取信息(self, 用户ID: str, 服务器ID: Optional[str] = None) -> Any:
        """
        获取目标用户信息。
        参数:
            用户ID: 目标用户 id。
            服务器ID: 可选，携带后返回该服务器内的昵称与角色。
        返回:
            用户信息字典。
        """
        查询参数: dict[str, Any] = {"user_id": 用户ID}
        if 服务器ID:
            查询参数["guild_id"] = 服务器ID
        return await self._请求("GET", "/user/view", 查询参数=查询参数)

    async def 下线(self) -> None:
        """
        下线机器人(仅限 Webhook 模式；WebSocket 模式断开即视为下线)。
        返回:
            无返回值。
        """
        await self._请求("POST", "/user/offline")

    async def 上线(self) -> None:
        """
        上线机器人(仅限 Webhook 模式；调用频率较低，请勿滥用)。
        返回:
            无返回值。
        """
        await self._请求("POST", "/user/online")

    async def 在线状态(self) -> Any:
        """
        获取机器人在线状态。
        返回:
            含 online(是否在线) 与 online_os(在线平台列表) 的 data 字典。
        """
        return await self._请求("GET", "/user/get-online-status")
