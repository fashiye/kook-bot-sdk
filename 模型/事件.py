'''
KOOK 事件对象模块：把网关推送的原始事件字典包装为便于调用的对象。
事件本身只携带数据；"回复/引用回复/私信作者"等便捷发送由机器人分发时注入的发送器驱动，
因此本模块保持模型层纯净、不依赖任何资源层实现。
'''
from typing import Any, Awaitable, Callable, Optional        # 提供 Any/Callable/Awaitable 类型注解
from .类型 import 消息类型                                     # 消息类型枚举，用于判断是否为系统事件


# 发送器回调签名：(事件, 内容, 消息类型, 是否引用原消息, 是否私信给作者) => 发送结果
发送器类型 = Callable[["事件", str | list | dict, Optional[int], bool, bool], Awaitable[Any]]


class 事件:
    """一条来自网关的 KOOK 事件。封装消息/系统事件通用字段的读取、分类与便捷回复。"""

    def __init__(self, 原始数据: dict[str, Any]):
        """
        解析网关推送的事件数据。
        参数:
            原始数据: WebSocket 信令 s=0 时 d 字段的原始字典。
        """
        # 原始事件字典，保留全部字段供高级用法直接读取
        self.原始数据 = 原始数据
        # 事件所属通道类型，GROUP=频道消息，PERSON=私信/单播消息
        self.通道类型: str = 原始数据.get("channel_type", "")
        # 事件类型编号，见消息类型枚举；255 代表系统事件
        self.类型: int = 原始数据.get("type", 0)
        # 发送目标：频道消息时为频道 id，系统事件时为服务器 id 等
        self.目标ID: str = 原始数据.get("target_id", "")
        # 发送者用户 id，系统事件时通常为 "1"
        self.作者ID: str = 原始数据.get("author_id", "")
        # 消息内容：文本为正文，图片/视频/文件为资源 url
        self.内容: str = 原始数据.get("content", "")
        # 消息唯一 id
        self.消息ID: str = 原始数据.get("msg_id", "")
        # 消息发送时间的毫秒时间戳
        self.时间戳: int = int(原始数据.get("msg_timestamp", 0))
        # 附加数据：普通消息含作者信息/服务器 id，系统事件含 type(事件名) 与 body
        self.附加数据: dict[str, Any] = 原始数据.get("extra", {}) if isinstance(原始数据.get("extra"), dict) else {}
        # 便捷发送器：由机器人分发入口注入，未注入时调用便捷发送会报错
        self._发送器: Optional[发送器类型] = None

    # ─── 便捷发送绑定 ───

    def 绑定发送器(self, 发送器: 发送器类型) -> None:
        """
        由机器人分发入口注入便捷发送回调(供 回复/引用回复/私信作者 使用)。
        参数:
            发送器: 见 发送器类型 说明；回调封装了 REST 客户端与通道路由逻辑。
        返回:
            无返回值。
        """
        self._发送器 = 发送器

    async def _便捷发送(self, 内容: str | list | dict, 类型: Optional[int],
                         引用: bool, 私信作者: bool) -> Any:
        """
        调用已注入的发送器执行一次便捷发送(三个公开便捷方法的统一内部入口)。
        参数:
            内容: 文本或卡片结构。
            类型: 消息类型，默认自动推断。
            引用: True 时带引用原消息。
            私信作者: True 时改为私信给事件作者。
        返回:
            发送接口的 data(含 msg_id)。
        异常:
            RuntimeError: 事件未绑定发送器(例如非机器人分发创建的事件)。
        """
        if self._发送器 is None:
            raise RuntimeError("事件未绑定发送器，便捷发送需由机器人分发出的事件提供")
        return await self._发送器(self, 内容, 类型, 引用, 私信作者)

    async def 回复(self, 内容: str | list | dict, 类型: Optional[int] = None) -> Any:
        """
        在事件发生的会话里回复(频道消息回频道，私信消息回给对方)。
        参数:
            内容: 文本或卡片结构。
            类型: 消息类型，默认自动推断。
        返回:
            发送接口的 data(含 msg_id)。
        """
        return await self._便捷发送(内容, 类型, False, False)

    async def 引用回复(self, 内容: str | list | dict, 类型: Optional[int] = None) -> Any:
        """
        引用原消息进行回复(同 回复，自动带 quote 关联)。
        参数:
            内容: 文本或卡片结构。
            类型: 消息类型，默认自动推断。
        返回:
            发送接口的 data(含 msg_id)。
        """
        return await self._便捷发送(内容, 类型, True, False)

    async def 私信作者(self, 内容: str | list | dict, 类型: Optional[int] = None) -> Any:
        """
        给本条消息的作者发私信。
        参数:
            内容: 文本或卡片结构。
            类型: 消息类型，默认自动推断。
        返回:
            发送接口的 data(含 msg_id)。
        """
        return await self._便捷发送(内容, 类型, False, True)

    # ─── 分类与字段 ───

    @property
    def 是否系统事件(self) -> bool:
        """判断是否为系统事件(type=255)。"""
        return self.类型 == 消息类型.系统.value

    @property
    def 系统事件名(self) -> str:
        """系统事件的具体事件名(extra.type)，非系统事件时返回空字符串。"""
        if self.是否系统事件:
            return str(self.附加数据.get("type", ""))
        return ""

    @property
    def 主体(self) -> dict[str, Any]:
        """
        事件主体：系统事件返回 extra.body；普通消息返回整条原始事件数据。
        按钮点击等系统事件通过该属性读取 value/user_id/msg_id/target_id 等字段。
        """
        if self.是否系统事件:
            主体: dict[str, Any] = self.附加数据.get("body", {})
            return 主体 if isinstance(主体, dict) else {}
        return self.原始数据

    def 匹配(self, 事件类型: int | str | None) -> bool:
        """
        判断事件是否匹配某个处理器注册的事件类型。
        参数:
            事件类型: 普通消息为消息类型整型值，系统事件为事件名字符串，None 表示匹配全部。
        返回:
            是否匹配。
        """
        if 事件类型 is None:
            return True
        if isinstance(事件类型, int):
            return (not self.是否系统事件) and self.类型 == 事件类型
        if isinstance(事件类型, str):
            return self.是否系统事件 and self.系统事件名 == 事件类型
        return False
