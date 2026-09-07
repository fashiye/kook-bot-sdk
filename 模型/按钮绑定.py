'''
KOOK 按钮回调绑定模块(模型层)：为"创建按钮时直接绑定回调"提供以按钮 value 为键的注册中心。
创建按钮元素(模型/卡片.py) 传入 回调 参数时会把 回调 登记到 按钮回调中心；
机器人收到 message_btn_click 事件后按 value 取出回调并调用，实现创建即绑定的语法糖。
'''
from typing import Callable, ClassVar, Optional     # 提供类型注解与类变量声明


class 按钮回调中心:
    """以按钮 value 为键的回调注册中心。同一 value 只保留最后一次绑定的回调(覆盖式注册)。

    类名即导出名；注册表存放于类属性，所有方法以类方法形式调用，
    因此 按钮回调中心.注册(值, 回调) 天然共享单例，无需额外创建实例。
    """

    # 回调表：键为按钮 value，值为创建按钮时绑定的处理函数
    _回调表: ClassVar[dict[str, Callable]] = {}

    @classmethod
    def 注册(cls, 值: str, 回调: Callable) -> None:
        """
        登记或覆盖某个按钮 value 的回调。
        参数:
            值: 按钮的 value 字段(需全局唯一，重复注册会覆盖旧回调)。
            回调: 创建按钮时绑定的处理函数，签名 async def 处理(事件) 或 def 处理(事件)。
        返回:
            无返回值。
        """
        cls._回调表[值] = 回调

    @classmethod
    def 取出(cls, 值: str) -> Optional[Callable]:
        """
        按按钮 value 取出绑定的回调。
        参数:
            值: 按钮的 value 字段。
        返回:
            绑定过的处理函数；未绑定时返回 None。
        """
        return cls._回调表.get(值)

    @classmethod
    def 移除(cls, 值: str) -> None:
        """
        移除某个按钮 value 的回调(订单等一次性交互结束后清理，避免注册表膨胀)。
        参数:
            值: 按钮的 value 字段。
        返回:
            无返回值。
        """
        cls._回调表.pop(值, None)

    @classmethod
    def 清空(cls) -> None:
        """清空全部按钮回调绑定。返回: 无返回值。"""
        cls._回调表.clear()
