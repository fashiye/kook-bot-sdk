'''
KOOK 语音资源模块：封装机器人加入/离开语音频道、语音连接保活及查询用户在语音频道 REST 接口。
参考文档:
- https://developer.kookapp.cn/doc/http/voice
- https://developer.kookapp.cn/doc/http/channel-user
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类


class 语音资源(资源基类):
    """语音分类资源：机器人语音推流(加入后获得媒体服务器地址)与频道状态查询。"""

    async def 加入(self, 频道ID: str, 密码: Optional[str] = None,
                   音频源标识: str = "1111", 音频负载类型: str = "111",
                   复用RTP端口: bool = True) -> Any:
        """
        让机器人加入语音频道并申请推流地址。
        参数:
            频道ID: 需要加入的语音频道 id。
            密码: 加密房间的进入密码，可选。
            音频源标识: RTP ssrc，默认 1111，不熟悉请勿改动。
            音频负载类型: RTP payload_type，默认 111，不熟悉请勿改动。
            复用RTP端口: 是否 rtcp 与 rtp 共用一个端口，默认 True。
        返回:
            含 ip/port/rtcp_mux/bitrate/audio_ssrc/audio_pt 的推流配置字典。
        """
        加入数据: dict[str, Any] = {"channel_id": 频道ID, "audio_ssrc": 音频源标识,
                                     "audio_pt": 音频负载类型, "rtcp_mux": 复用RTP端口}
        if 密码:
            加入数据["password"] = 密码
        return await self._请求("POST", "/voice/join", 数据=加入数据)

    async def 已加入列表(self) -> Any:
        """
        获取机器人当前加入的语音频道列表。
        返回:
            含 items(频道列表) 与 meta 的 data 字典。
        """
        return await self._请求("GET", "/voice/list")

    async def 离开(self, 频道ID: str) -> None:
        """
        让机器人主动离开语音频道并释放推流资源。
        参数:
            频道ID: 需要离开的语音频道 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/voice/leave", 数据={"channel_id": 频道ID})

    async def 保持活跃(self, 频道ID: str) -> None:
        """
        保持语音连接活跃(约每 45 秒调用，防止系统回收推流端口资源)。
        参数:
            频道ID: 需要保活的语音频道 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/voice/keep-alive", 数据={"channel_id": 频道ID})

    async def 获取用户所在语音频道(self, 服务器ID: str, 用户ID: str,
                                   页码: int = 1, 页大小: int = 50) -> Any:
        """
        根据用户与服务器 id 查询该用户所在的语音频道(不在则返回空)。
        参数:
            服务器ID: 服务器 id。
            用户ID: 目标用户 id。
            页码: 目标页数。
            页大小: 每页数据数量。
        返回:
            含 items(频道列表) 与 meta 的 data 字典。
        """
        return await self._请求("GET", "/channel-user/get-joined-channel",
                                查询参数={"guild_id": 服务器ID, "user_id": 用户ID,
                                          "page": 页码, "page_size": 页大小})
