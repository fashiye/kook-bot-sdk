'''
KOOK 类型化对象模块：把 REST 返回的原始字典包装成带中文属性访问的数据对象。
对象保留原始字典(原始数据)供高级用法，同时把常用字段提为属性；字段缺失时安全降级为默认值。
'''
from dataclasses import dataclass, field                     # 提供数据类支持，简化对象定义
from datetime import datetime                                # 提供时间戳换算
from typing import Any, Optional                             # 提供 Any/Optional 类型注解

from .类型 import 消息类型, 频道类型                           # 类型枚举，用于字段语义说明


def 时间戳转时间(毫秒值: Any) -> Optional[datetime]:
    """
    把毫秒时间戳转为本地 datetime(工具函数，供各对象的时间属性复用)。
    参数:
        毫秒值: 毫秒时间戳(数字或字符串)。
    返回:
        本地时间对象；无效输入返回 None。
    """
    try:
        # 调用库函数：把毫秒时间戳换算为时间对象
        # 传入：秒级时间戳
        # 作用：把整数时间戳转为可读 datetime
        # 传出：本地时区 datetime 对象
        return datetime.fromtimestamp(int(毫秒值) / 1000)
    except (TypeError, ValueError):
        return None


@dataclass
class 用户对象:
    """KOOK 用户信息对象：REST 用户字典的面向对象视图。"""
    id: str = ""
    用户名: str = ""
    认证号: str = ""
    昵称: str = ""
    头像: str = ""
    vip头像: str = ""
    是否在线: bool = False
    状态: int = 0
    是否机器人: bool = False
    角色列表: list = field(default_factory=list)
    原始数据: dict = field(default_factory=dict)

    @classmethod
    def 解析(cls, 字典: Optional[dict]) -> "用户对象":
        """从用户字典构造对象；空值返回空对象。"""
        if not isinstance(字典, dict):
            return cls()
        号码: str = str(字典.get("identify_num") or "")
        return cls(
            id=str(字典.get("id") or ""),
            用户名=str(字典.get("username") or ""),
            认证号=号码,
            昵称=str(字典.get("nickname") or 字典.get("username") or ""),
            头像=str(字典.get("avatar") or ""),
            vip头像=str(字典.get("vip_avatar") or ""),
            是否在线=bool(字典.get("online")),
            状态=int(字典.get("status") or 0),
            是否机器人=bool(字典.get("bot")),
            角色列表=list(字典.get("roles") or []),
            原始数据=字典,
        )

    @property
    def 全名(self) -> str:
        """用户名#认证号 形式的全名。"""
        return f"{self.用户名}#{self.认证号}" if self.认证号 else self.用户名


@dataclass
class 频道对象:
    """KOOK 频道信息对象：channel/view 或列表元素等频道字典的对象视图。"""
    id: str = ""
    服务器id: str = ""
    创建者id: str = ""
    父频道id: str = ""
    名称: str = ""
    简介: str = ""
    类型值: int = 频道类型.文字.value
    排序: int = 0
    人数上限: int = 0
    是否分组: bool = False
    是否加密: bool = False
    慢速模式: int = 0
    原始数据: dict = field(default_factory=dict)

    @classmethod
    def 解析(cls, 字典: Optional[dict]) -> "频道对象":
        """从频道字典构造对象；空值返回空对象。"""
        if not isinstance(字典, dict):
            return cls()
        return cls(
            id=str(字典.get("id") or ""),
            服务器id=str(字典.get("guild_id") or ""),
            创建者id=str(字典.get("user_id") or ""),
            父频道id=str(字典.get("parent_id") or ""),
            名称=str(字典.get("name") or ""),
            简介=str(字典.get("topic") or ""),
            类型值=int(字典.get("type") or 频道类型.文字.value),
            排序=int(字典.get("level") or 0),
            人数上限=int(字典.get("limit_amount") or 0),
            是否分组=bool(字典.get("is_category")),
            是否加密=bool(字典.get("has_password")),
            慢速模式=int(字典.get("slow_mode") or 0),
            原始数据=字典,
        )

    @property
    def 类型(self) -> Optional[频道类型]:
        """频道类型枚举(无法识别返回 None)。"""
        try:
            return 频道类型(self.类型值)
        except ValueError:
            return None


@dataclass
class 服务器对象:
    """KOOK 服务器信息对象：guild/view 或列表元素等服务器字典的对象视图。"""
    id: str = ""
    名称: str = ""
    主题: str = ""
    图标: str = ""
    服务器主id: str = ""
    通知类型: int = 0
    默认频道id: str = ""
    欢迎频道id: str = ""
    助力数: int = 0
    等级: int = 0
    原始数据: dict = field(default_factory=dict)

    @classmethod
    def 解析(cls, 字典: Optional[dict]) -> "服务器对象":
        """从服务器字典构造对象；空值返回空对象。"""
        if not isinstance(字典, dict):
            return cls()
        return cls(
            id=str(字典.get("id") or ""),
            名称=str(字典.get("name") or ""),
            主题=str(字典.get("topic") or ""),
            图标=str(字典.get("icon") or ""),
            服务器主id=str(字典.get("user_id") or ""),
            通知类型=int(字典.get("notify_type") or 0),
            默认频道id=str(字典.get("default_channel_id") or ""),
            欢迎频道id=str(字典.get("welcome_channel_id") or ""),
            助力数=int(字典.get("boost_num") or 0),
            等级=int(字典.get("level") or 0),
            原始数据=字典,
        )


@dataclass
class 消息对象:
    """KOOK 消息详情对象：频道/私信消息字典的对象视图(取自 REST view/detail 返回)。"""
    id: str = ""
    类型值: int = 消息类型.KMD文本.value
    内容: str = ""
    作者id: str = ""
    频道id: str = ""
    创建时间毫秒: int = 0
    是否已读: bool = False
    引用数据: dict = field(default_factory=dict)
    原始数据: dict = field(default_factory=dict)

    @classmethod
    def 解析(cls, 字典: Optional[dict]) -> "消息对象":
        """从消息字典构造对象；空值返回空对象。"""
        if not isinstance(字典, dict):
            return cls()
        return cls(
            id=str(字典.get("id") or ""),
            类型值=int(字典.get("type") or 消息类型.KMD文本.value),
            内容=str(字典.get("content") or ""),
            作者id=str(字典.get("author_id") or (字典.get("author") or {}).get("id") or ""),
            频道id=str(字典.get("channel_id") or ""),
            创建时间毫秒=int(字典.get("create_at") or 0),
            是否已读=bool(字典.get("read_status")),
            引用数据=字典.get("quote") if isinstance(字典.get("quote"), dict) else {},
            原始数据=字典,
        )

    @property
    def 类型(self) -> Optional[消息类型]:
        """消息类型枚举(无法识别返回 None)。"""
        try:
            return 消息类型(self.类型值)
        except ValueError:
            return None

    @property
    def 创建时间(self) -> Optional[datetime]:
        """消息创建时间(毫秒时间戳换算)。"""
        return 时间戳转时间(self.创建时间毫秒)
