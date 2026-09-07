'''
KOOK 机器人聚合客户端模块：以 Bot 令牌鉴权，按域装配全部可用分类资源供业务直接调用。
资源层内各分类对象共享本客户端唯一的会话与鉴权头，业务调用形如
    self.API.频道消息.发送(...)  /  self.API.服务器.获取详情(...)
'''
from typing import Any                               # 提供 Any 类型注解(请求返回任意 JSON 结构)

from ..核心.HTTP引擎 import HTTP引擎                   # 底层 REST 请求引擎
from .消息.频道消息 import 频道消息资源                 # 频道消息资源
from .消息.私信 import 私信消息资源, 私信会话资源       # 私信消息与私聊会话资源
from .服务器.服务器 import 服务器资源                   # 服务器资源(含静音/助力)
from .服务器.角色 import 服务器角色资源                 # 服务器角色资源
from .服务器.表情 import 服务器表情资源                 # 服务器表情资源
from .服务器.邀请 import 邀请资源                      # 邀请资源
from .频道.频道 import 频道资源                        # 频道资源
from .频道.频道角色权限 import 频道角色权限资源          # 频道角色权限资源
from .频道.语音 import 语音资源                         # 语音资源(含查询用户在语音频道)
from .用户 import 用户资源                              # 用户资源
from .素材 import 素材资源                              # 素材上传资源
from .帖子 import 帖子资源                              # 帖子资源
from .模板 import 模板资源                              # 消息模板资源


class HTTP客户端(HTTP引擎):
    """机器人 HTTP 客户端：以 Bot 令牌鉴权，聚合机器人可用的全部分类资源。"""

    def __init__(self, 令牌: str):
        """
        初始化机器人客户端。
        参数:
            令牌: KOOK 机器人令牌。
        """
        super().__init__(令牌, 鉴权前缀="Bot")
        # 装配各分类资源对象：它们共享本客户端唯一的会话与鉴权头
        self.频道消息: 频道消息资源 = 频道消息资源(self)
        self.私信消息: 私信消息资源 = 私信消息资源(self)
        self.私信会话: 私信会话资源 = 私信会话资源(self)
        self.服务器: 服务器资源 = 服务器资源(self)
        self.服务器角色: 服务器角色资源 = 服务器角色资源(self)
        self.服务器表情: 服务器表情资源 = 服务器表情资源(self)
        self.邀请: 邀请资源 = 邀请资源(self)
        self.频道: 频道资源 = 频道资源(self)
        self.频道角色权限: 频道角色权限资源 = 频道角色权限资源(self)
        self.用户: 用户资源 = 用户资源(self)
        self.语音: 语音资源 = 语音资源(self)
        self.素材: 素材资源 = 素材资源(self)
        self.帖子: 帖子资源 = 帖子资源(self)
        self.模板: 模板资源 = 模板资源(self)
        # 频道名称→id 解析缓存：{服务器id: {频道名称: 频道id}}，避免重复请求列表
        self.频道名称缓存: dict[str, dict[str, str]] = {}
        # 服务器名称→id 解析缓存：{服务器名称: 服务器id}
        self.服务器名称缓存: dict[str, str] = {}

    async def 解析频道ID(self, 服务器ID: str, 频道标识: str) -> str:
        """
        把频道 id 或频道名称解析为频道 id(名称查询带缓存)。
        纯数字 id 直接返回；名称匹配以服务器频道列表中第一个同名频道为准。
        参数:
            服务器ID: 频道所在服务器 id。
            频道标识: 频道 id 或频道名称。
        返回:
            频道 id。
        异常:
            ValueError: 服务器下未找到该名称的频道。
        """
        标识: str = str(频道标识).strip()
        # 纯数字视为 id，直接返回
        if 标识.isdigit():
            return 标识
        # 命中名称缓存则直接返回
        名称缓存: dict[str, str] = self.频道名称缓存.setdefault(服务器ID, {})
        if 标识 in 名称缓存:
            return 名称缓存[标识]
        # 拉取服务器全量频道列表按名称匹配(自动翻页)
        频道列表: Any = await self.频道.获取列表(服务器ID, 合并全部分页=True)
        for 频道字典 in 频道列表:
            if str(频道字典.get("name", "")) == 标识:
                名称缓存[标识] = str(频道字典.get("id", ""))
                return 名称缓存[标识]
        raise ValueError(f"服务器 {服务器ID} 下未找到名为「{标识}」的频道")

    async def 解析服务器ID(self, 服务器标识: str) -> str:
        """
        把服务器 id 或服务器名称解析为服务器 id(名称查询带缓存)。
        参数:
            服务器标识: 服务器 id 或服务器名称。
        返回:
            服务器 id。
        异常:
            ValueError: 未找到该名称的服务器。
        """
        标识: str = str(服务器标识).strip()
        if 标识.isdigit():
            return 标识
        if 标识 in self.服务器名称缓存:
            return self.服务器名称缓存[标识]
        服务器列表: Any = await self.服务器.获取列表(合并全部分页=True)
        for 服务器字典 in 服务器列表:
            if str(服务器字典.get("name", "")) == 标识:
                self.服务器名称缓存[标识] = str(服务器字典.get("id", ""))
                return self.服务器名称缓存[标识]
        raise ValueError(f"未找到名为「{标识}」的服务器")

    async def 获取网关地址(self) -> str:
        """
        获取 WebSocket 网关连接地址。
        返回:
            网关 URL，compress=0 保证数据明文文本而非 zlib 压缩。
        """
        结果: Any = await self.请求("GET", "/gateway/index", 查询参数={"compress": 0})
        return str(结果.get("url", ""))
