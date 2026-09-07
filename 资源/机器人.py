'''
KOOK 机器人主模块：组合 REST 聚合客户端与 WebSocket 网关，提供事件注册/分发、启停管理，
以及便捷消息发送、命令/关键词路由与"等待回复"交互等语法糖。
'''
import asyncio                                            # 提供事件循环/等待器与异步控制
import logging                                            # 提供日志输出
from typing import Any, Awaitable, Callable, Optional     # 提供类型注解

from .客户端 import HTTP客户端                              # KOOK REST 聚合客户端
from ..模型.类型 import 消息类型, 系统事件名                 # 消息类型与系统事件名枚举
from ..核心.网关 import 网关                                # KOOK WebSocket 网关客户端
from ..模型.事件 import 事件, 发送器类型                     # 事件对象与便捷发送器回调类型
from ..模型.错误 import 令牌错误                            # 令牌鉴权错误


# 机器人模块日志器
_logger: logging.Logger = logging.getLogger("kook库.机器人")

# 文本消息过滤集合：纯文本(1)与 KMD 文本(9)，私信/频道通用
文本消息过滤: frozenset[int] = frozenset({消息类型.纯文本.value, 消息类型.KMD文本.value})

# 图片类扩展名集合(按扩展名自动推断图片消息)
图片扩展集合: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico"})
# 视频类扩展名集合(asset 上传支持的视频格式)
视频扩展集合: frozenset[str] = frozenset({".mp4", ".mov"})


def 推断媒体类型(名称: Optional[str]) -> int:
    """
    按文件名扩展名推断应使用的消息类型(语法糖内部工具)。
    参数:
        名称: 文件名或资源 url。
    返回:
        消息类型：图片2 / 视频3 / 其它一律按文件4。
    """
    小写名: str = (名称 or "").lower()
    if 小写名.endswith(tuple(图片扩展集合)):
        return 消息类型.图片.value
    if 小写名.endswith(tuple(视频扩展集合)):
        return 消息类型.视频.value
    return 消息类型.文件.value


class 机器人:
    """
    KOOK 机器人主类。
    启动后同时提供 REST 调用(self.API)与实时事件分发；处理器通过装饰器注册。
    事件处理器可直接使用 事件.回复/事件.引用回复/事件.私信作者 便捷发送。
    """

    def __init__(self, 令牌: str):
        """
        初始化机器人。
        参数:
            令牌: KOOK 机器人令牌。
        """
        # REST 客户端(聚合各分类资源)，供业务直接调用发送/编辑等接口
        self.API: HTTP客户端 = HTTP客户端(令牌)
        # WebSocket 网关实例，打开后创建
        self.网关: Optional[网关] = None
        # 事件处理器注册表：每项为(允许的事件类型集合, 回调)；None 集合代表接收全部事件
        self.处理器列表: list[tuple[Optional[frozenset], Callable[[事件], Awaitable[None]]]] = []
        # 等待器注册表：每项为(谓词, 完成信号 Future)；事件满足谓词时被唤醒
        self.等待器列表: list[tuple[Callable[[事件], bool], "asyncio.Future[事件]"]] = []
        # 启动成功后的回调列表(接收机器人自身为参数)
        self.启动回调列表: list[Callable[["机器人"], Awaitable[None]]] = []
        # 关闭前的回调列表(接收机器人自身为参数)
        self.关闭回调列表: list[Callable[["机器人"], Awaitable[None]]] = []
        # 停止事件：运行时置位，用于结束 运行()
        self.停止事件 = asyncio.Event()

    # ─── 事件注册装饰器 ───

    def 注册处理器(self, 事件类型: int | str | None = None):
        """
        注册一个事件处理器(装饰器用法)。
        参数:
            事件类型: 普通消息类型编号(int，见消息类型枚举)；
                      系统事件名(str，见系统事件名枚举)；
                      None 表示匹配所有事件。
        返回:
            装饰器，用于包裹异步处理函数，处理器接收一个 事件 对象参数。
        """
        # 把单个类型包装成集合；None 代表不限类型
        过滤集合: Optional[frozenset] = None if 事件类型 is None else frozenset({事件类型})

        def 包装(处理器: Callable[[事件], Awaitable[None]]) -> Callable[[事件], Awaitable[None]]:
            self.处理器列表.append((过滤集合, 处理器))
            return 处理器

        return 包装

    def 文本消息(self):
        """便捷注册：监听频道/私信的文字消息(类型 1 纯文本与 9 KMD 文本)。返回: 装饰器。"""
        # 注册同时匹配两个文本消息类型
        def 包装(处理器: Callable[[事件], Awaitable[None]]) -> Callable[[事件], Awaitable[None]]:
            self.处理器列表.append((文本消息过滤, 处理器))
            return 处理器

        return 包装

    def 命令(self, 命令文本: str):
        """
        便捷注册：命令路由(仅文本消息)，处理器接收 (事件, 命令参数)。
        触发条件为消息文本去掉首尾空白后以 命令文本 开头。
        参数:
            命令文本: 命令前缀，如 "!ping"。
        返回:
            装饰器，处理器签名 async def 处理(事件: 事件, 参数: str)。
        """
        def 包装(处理器: Callable[[事件, str], Awaitable[None]]) -> Callable[[事件, str], Awaitable[None]]:
            async def 路由(当前事件: 事件) -> None:
                # 消息正文去掉首尾空白；匹配前缀则截取剩余部分作为参数
                正文: str = str(当前事件.内容).strip()
                if 正文.startswith(命令文本):
                    await 处理器(当前事件, 正文[len(命令文本):].strip())

            self.处理器列表.append((文本消息过滤, 路由))
            return 处理器

        return 包装

    def 关键词(self, 关键词文本: str):
        """
        便捷注册：包含关键词的文本消息路由，处理器接收 (事件)。
        参数:
            关键词文本: 消息正文中需包含的文本。
        返回:
            装饰器，处理器签名 async def 处理(事件: 事件)。
        """
        def 包装(处理器: Callable[[事件], Awaitable[None]]) -> Callable[[事件], Awaitable[None]]:
            async def 路由(当前事件: 事件) -> None:
                if 关键词文本 in str(当前事件.内容):
                    await 处理器(当前事件)

            self.处理器列表.append((文本消息过滤, 路由))
            return 处理器

        return 包装

    def 按钮点击(self):
        """便捷注册：监听卡片按钮点击系统事件(message_btn_click)。返回: 装饰器。"""
        return self.注册处理器(系统事件名.按钮点击)

    # ─── 启动/关闭钩子 ───

    def 启动时(self, 处理器: Callable[["机器人"], Awaitable[None]]) -> Callable[["机器人"], Awaitable[None]]:
        """注册连接成功后的启动钩子。返回: 原处理函数。"""
        self.启动回调列表.append(处理器)
        return 处理器

    def 关闭时(self, 处理器: Callable[["机器人"], Awaitable[None]]) -> Callable[["机器人"], Awaitable[None]]:
        """注册关闭前的清理钩子。返回: 原处理函数。"""
        self.关闭回调列表.append(处理器)
        return 处理器

    # ─── 便捷发送(语法糖) ───

    async def 发送频道(self, 频道ID: str, 内容: str | list | dict,
                        类型: Optional[int] = None, 引用消息ID: Optional[str] = None) -> Any:
        """
        便捷：向频道发送文本或卡片消息(= API.频道消息.发送)。
        参数:
            频道ID: 目标频道 id。
            内容: 文本，或卡片数组/字典(自动按卡片类型发送)。
            类型: 消息类型，默认自动推断。
            引用消息ID: 引用回复的源消息 id。
        返回:
            发送接口的 data(含 msg_id)。
        """
        return await self.API.频道消息.发送(频道ID, 内容, 类型=类型, 引用消息ID=引用消息ID)

    async def 发送私信(self, 用户ID: str, 内容: str | list | dict,
                        类型: Optional[int] = None) -> Any:
        """
        便捷：向用户发送私信(= API.私信消息.发送)。
        参数:
            用户ID: 目标用户 id。
            内容: 文本或卡片结构。
            类型: 消息类型，默认自动推断。
        返回:
            发送接口的 data(含 msg_id)。
        """
        return await self.API.私信消息.发送(内容, 目标用户ID=用户ID, 类型=类型)

    async def _媒体地址(self, 来源: str | bytes, 文件名: Optional[str]) -> str:
        """
        把媒体来源统一转为可发送的资源 url(便捷媒体发送的内部工具)。
        参数:
            来源: http(s) 开头的站内资源 url，本地文件路径，或文件字节。
            文件名: 字节来源必需，用于扩展名与上传展示；路径来源可空。
        返回:
            资源 url；本地来源会先上传到素材库。
        异常:
            ValueError: 字节来源未提供文件名或本地路径无效。
        """
        # 已上传的站内 url 直接使用
        if isinstance(来源, str) and (来源.startswith("http://") or 来源.startswith("https://")):
            return 来源
        if isinstance(来源, str):
            # 本地文件路径：读取字节
            try:
                # 调用库函数：读取本地文件为二进制
                # 传入：文件路径(来源)
                # 作用：把磁盘图片/文件读入内存供上传
                # 传出：bytes 文件内容
                with open(来源, "rb") as 文件对象:
                    文件字节: bytes = 文件对象.read()
                    文件名 = 文件名 or 来源.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            except OSError as 异常:
                raise ValueError(f"无法读取本地媒体文件 {来源}: {异常}") from 异常
        else:
            文件字节 = 来源
        if not 文件名:
            raise ValueError("发送字节媒体时必须提供 文件名(含扩展名)")
        # 先上传素材换取站内地址
        上传结果: Any = await self.API.素材.上传(文件字节, 文件名)
        return str(上传结果.get("url", ""))

    async def 发送媒体(self, 频道ID: str, 来源: str | bytes, 文件名: Optional[str] = None,
                        类型: Optional[int] = None) -> Any:
        """
        便捷：向频道发送本地文件/字节媒体，自动上传并按类型发送(= 素材上传 + 频道消息)。
        参数:
            频道ID: 目标频道 id。
            来源: 本地文件路径、文件字节，或已上传的 http(s) 资源 url。
            文件名: 字节来源必需(带扩展名)；可空时按来源推断。
            类型: 消息类型(图片2/视频3/文件4)，None 按扩展名自动推断。
        返回:
            发送接口的 data(含 msg_id)。
        """
        资源地址: str = await self._媒体地址(来源, 文件名)
        return await self.API.频道消息.发送(频道ID, 资源地址,
                                            类型=类型 if 类型 is not None else 推断媒体类型(文件名 or 资源地址))

    async def 私信媒体(self, 用户ID: str, 来源: str | bytes, 文件名: Optional[str] = None,
                        类型: Optional[int] = None) -> Any:
        """
        便捷：向用户私信发送本地文件/字节媒体(= 素材上传 + 私信消息)。
        参数:
            用户ID: 目标用户 id。
            来源: 本地文件路径、文件字节，或已上传的 http(s) 资源 url。
            文件名: 字节来源必需(带扩展名)。
            类型: 消息类型(图片2/视频3/文件4)，None 按扩展名自动推断。
        返回:
            发送接口的 data(含 msg_id)。
        """
        资源地址: str = await self._媒体地址(来源, 文件名)
        return await self.API.私信消息.发送(资源地址, 目标用户ID=用户ID,
                                             类型=类型 if 类型 is not None else 推断媒体类型(文件名))

    async def _事件发送器(self, 事件对象: 事件, 内容: str | list | dict,
                          类型: Optional[int], 引用: bool, 私信作者: bool) -> Any:
        """
        事件便捷发送的内部实现(由 事件.回复/引用回复/私信作者 调用)。
        按事件来源通道自动路由：频道消息回频道、私信回对方、指定则私信作者。
        参数:
            事件对象: 触发发送的原始事件。
            内容: 文本或卡片结构。
            类型: 消息类型。
            引用: 是否带引用原消息。
            私信作者: 是否改为私信给作者。
        返回:
            发送接口的 data(含 msg_id)。
        异常:
            RuntimeError: 系统事件或未知通道类型无法定位回复目标。
        """
        if 事件对象.是否系统事件:
            raise RuntimeError("系统事件无会话目标，无法便捷回复")
        # 目标用户：私信/私信作者都发给消息作者
        对方用户ID: str = 事件对象.作者ID or 事件对象.目标ID
        if 私信作者 or 事件对象.通道类型 == "PERSON":
            return await self.API.私信消息.发送(
                内容, 目标用户ID=对方用户ID, 类型=类型,
                引用消息ID=事件对象.消息ID if 引用 else None)
        if 事件对象.通道类型 == "GROUP":
            return await self.API.频道消息.发送(
                事件对象.目标ID, 内容, 类型=类型,
                引用消息ID=事件对象.消息ID if 引用 else None)
        raise RuntimeError(f"未知通道类型({事件对象.通道类型})，无法便捷回复")

    # ─── 等待事件(交互语法糖) ───

    async def 等待事件(self, 谓词: Callable[[事件], bool], 超时秒: float = 60) -> Optional[事件]:
        """
        等待下一个满足条件的事件，适合做一问一答式交互。
        参数:
            谓词: 判断函数，接收 事件 返回是否命中。
            超时秒: 最长等待秒数，默认 60。
        返回:
            命中事件；超时返回 None。
        """
        # 创建完成信号并登记等待器
        信号: "asyncio.Future[事件]" = asyncio.get_running_loop().create_future()
        self.等待器列表.append((谓词, 信号))
        try:
            # 调用库方法：等待带超时的 Future 完成
            # 传入：可等待对象 信号(事件), 超时秒
            # 作用：阻塞到事件命中或超时
            # 传出：Future 结果(事件对象)；超时抛 TimeoutError
            return await asyncio.wait_for(信号, 超时秒)
        except asyncio.TimeoutError:
            return None
        finally:
            # 无论结果如何都移除该等待器，避免泄漏
            self.等待器列表 = [(匹配, 待完成) for 匹配, 待完成 in self.等待器列表 if 待完成 is not 信号]

    async def 等待文本(self, 关键词: Optional[str] = None, 频道ID: Optional[str] = None,
                        作者ID: Optional[str] = None, 超时秒: float = 60) -> Optional[事件]:
        """
        等待下一条符合过滤条件的文本消息。
        参数:
            关键词: 仅接收正文含该关键词的消息，None 不限制。
            频道ID: 仅接收该频道的消息，None 不限制。
            作者ID: 仅接收该作者的消息，None 不限制。
            超时秒: 最长等待秒数，默认 60。
        返回:
            命中的文本消息事件；超时返回 None。
        """
        def 谓词(当前事件: 事件) -> bool:
            # 仅文本消息；随后逐项套用过滤条件
            if not any(当前事件.匹配(类型) for 类型 in 文本消息过滤):
                return False
            if 频道ID and 当前事件.目标ID != 频道ID:
                return False
            if 作者ID and 当前事件.作者ID != 作者ID:
                return False
            if 关键词 and 关键词 not in str(当前事件.内容):
                return False
            return True

        return await self.等待事件(谓词, 超时秒)

    async def 等待按钮点击(self, 值: str, 超时秒: float = 60) -> Optional[事件]:
        """
        等待某按钮(value 匹配)被点击的系统事件。
        参数:
            值: 目标按钮回传的 value。
            超时秒: 最长等待秒数，默认 60。
        返回:
            按钮点击系统事件(主体含 value/user_id 等)；超时返回 None。
        """
        def 谓词(当前事件: 事件) -> bool:
            # 需为按钮点击系统事件且 value 一致
            return (当前事件.系统事件名 == 系统事件名.按钮点击
                    and str(当前事件.主体.get("value", "")) == 值)

        return await self.等待事件(谓词, 超时秒)

    # ─── 事件分发 ───

    async def _处理网关事件(self, 事件数据: dict[str, Any]) -> None:
        """网关回调入口：包装事件、唤醒等待器、注入发送器并分发到匹配的处理器。"""
        当前事件 = 事件(事件数据)
        # 注入便捷发送器，使 事件.回复 等语法糖可用
        当前事件.绑定发送器(self._事件发送器)
        # 先喂给等待器：命中的置位并移出注册表
        for 谓词, 信号 in list(self.等待器列表):
            if not 信号.done() and 谓词(当前事件):
                信号.set_result(当前事件)
        self.等待器列表 = [(匹配, 待完成) for 匹配, 待完成 in self.等待器列表 if not 待完成.done()]
        # 再分发给注册处理器
        for 过滤集合, 处理器 in self.处理器列表:
            try:
                if 过滤集合 is None or any(当前事件.匹配(类型) for 类型 in 过滤集合):
                    await 处理器(当前事件)
            except Exception as 异常:
                _logger.exception("事件处理器异常(%s): %s", getattr(处理器, "__name__", 处理器), 异常)

    # ─── 生命周期 ───

    async def 打开(self) -> None:
        """打开 HTTP 会话、启动网关并触发启动钩子。返回: 无返回值。"""
        await self.API.打开()
        # 创建网关并把本类的分发方法作为事件回调
        self.网关 = 网关(self.API, self._处理网关事件)
        await self.网关.启动()
        _logger.info("机器人已启动")
        # 依次触发启动钩子
        for 处理器 in self.启动回调列表:
            try:
                await 处理器(self)
            except Exception as 异常:
                _logger.exception("启动钩子异常: %s", 异常)

    async def 关闭(self) -> None:
        """触发关闭钩子，停止网关并关闭 HTTP 会话。返回: 无返回值。"""
        _logger.info("机器人正在关闭")
        for 处理器 in self.关闭回调列表:
            try:
                await 处理器(self)
            except Exception as 异常:
                _logger.exception("关闭钩子异常: %s", 异常)
        if self.网关 is not None:
            await self.网关.停止()
        await self.API.关闭()

    async def _启动并等待(self) -> None:
        """内部运行流程：打开→等待停止信号→关闭。返回: 无返回值。"""
        try:
            await self.打开()
            await self.停止事件.wait()
        except 令牌错误:
            _logger.error("令牌无效，机器人无法启动")
        finally:
            await self.关闭()

    def 运行(self) -> None:
        """以阻塞方式运行机器人，直到收到停止信号或进程退出。返回: 无返回值。"""
        # 调用库函数：运行异步主流程
        # 传入：协程 _启动并等待()
        # 作用：创建事件循环并执行，结束后关闭循环
        # 传出：无返回值
        asyncio.run(self._启动并等待())

    def 请求停止(self) -> None:
        """请求机器人优雅停止(供运行在其他事件循环中的调用方使用)。返回: 无返回值。"""
        self.停止事件.set()
        if self.网关 is not None:
            # 直接调度网关停止协程到其事件循环执行
            asyncio.create_task(self.网关.停止())
