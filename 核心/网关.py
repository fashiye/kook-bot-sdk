'''
KOOK WebSocket 网关模块：负责连接网关、握手、心跳保活、按序接收事件以及断线自动重连。
协议参考: https://developer.kookapp.cn/doc/websocket
'''
import asyncio                                            # 提供异步任务/事件/超时控制
import json                                               # 提供 JSON 解析，用于解包信令帧
import logging                                            # 提供日志输出
import random                                             # 提供心跳间隔随机抖动(30±5 秒)
from typing import Any, Callable, Awaitable, Optional     # 提供类型注解

from ..模型.错误 import 令牌错误                                # 令牌鉴权错误


# 网关模块日志器
_logger: logging.Logger = logging.getLogger("kook库.网关")


class _要求重连(Exception):
    """网关内部信号：收到服务端 reconnect 信令或心跳超时，需要断开并重新建立全新会话。"""


class 网关:
    """
    KOOK WebSocket 网关客户端。
    负责连接(可重连)、心跳、事件帧的 sn 有序处理，并把每条事件字典交给上层回调。
    """

    def __init__(self, HTTP客户端: "HTTP客户端", 事件处理器: Callable[[dict[str, Any]], Awaitable[None]]):
        """
        初始化网关。
        参数:
            HTTP客户端: 已打开的 KOOK HTTP 客户端，复用其 aiohttp 会话并借其获取网关地址。
            事件处理器: 异步回调，接收每条已排序的事件字典。
        """
        self.HTTP客户端 = HTTP客户端
        # 上层事件回调，网关保证按 sn 顺序调用
        self.事件处理器 = 事件处理器
        # 服务端分配的会话 id，用于将来扩展 resume 断线续传
        self.会话ID: Optional[str] = None
        # 已成功交给上层处理的最大 sn，用于去重与缺口判断
        self.最大sn: int = 0
        # 乱序事件暂存区，键为 sn，值为事件帧，用于等待前面的缺口补齐
        self.暂存区: dict[int, dict[str, Any]] = {}
        # 停止信号，设置后主循环与心跳退出
        self.停止事件 = asyncio.Event()
        # 心跳 pong 到达信号
        self._pong事件 = asyncio.Event()
        # 主循环与心跳任务引用，便于停止时取消
        self._主任务: Optional[asyncio.Task] = None
        self._心跳任务: Optional[asyncio.Task] = None

    # ─── 生命周期 ───

    async def 启动(self) -> None:
        """启动网关主循环任务。返回: 无返回值。"""
        # 重置停止标志(若曾停止过)
        self.停止事件.clear()
        # 调用库函数：创建异步任务
        # 传入：协程函数 主循环()
        # 作用：把主循环放到后台并发执行
        # 传出：asyncio.Task 对象
        self._主任务 = asyncio.create_task(self._主循环())

    async def 停止(self) -> None:
        """停止网关：置停止标志并关闭当前连接。返回: 无返回值。"""
        self.停止事件.set()
        if self._主任务 is not None:
            self._主任务.cancel()
            try:
                # 调用库方法：等待任务结束
                # 传入：无
                # 作用：等待被取消的任务真正退出
                # 传出：无返回值(任务被取消时抛 CancelledError)
                await self._主任务
            except asyncio.CancelledError:
                pass

    async def 等待退出(self) -> None:
        """阻塞直到主循环任务结束。返回: 无返回值。"""
        if self._主任务 is not None:
            await self._主任务

    # ─── 主循环与重连 ───

    async def _主循环(self) -> None:
        """连接主循环：获取网关地址→连接→运行，失败按退避策略重试直到停止。"""
        # 连续失败的重试延时，初始 1 秒，最大 60 秒
        退避秒数: float = 1.0
        while not self.停止事件.is_set():
            try:
                # 调用库方法：请求新网关地址
                # 传入：无
                # 作用：向 KOOK 申请一条网关连接 url(compress=0 明文)
                # 传出：str 类型 ws 地址
                网关地址: str = await self.HTTP客户端.获取网关地址()
                if self.HTTP客户端.会话 is None:
                    raise RuntimeError("HTTP 会话未打开")
                # 调用库方法：建立 WebSocket 连接
                # 传入：url(网关地址)
                # 作用：握手建立长连接，失败会抛异常
                # 传出：aiohttp ClientWebSocketResponse 对象(支持上下文管理自动断开)
                async with self.HTTP客户端.会话.ws_connect(网关地址) as 连接:
                    # 连接成功后清零退避，并进入本次连接的消息循环
                    退避秒数 = 1.0
                    await self._运行连接(连接)
            except 令牌错误:
                _logger.error("网关令牌校验失败，停止重连")
                break
            except _要求重连:
                _logger.warning("服务端要求重连或心跳超时，稍后建立全新会话")
            except asyncio.CancelledError:
                raise
            except Exception as 异常:
                _logger.warning("网关连接异常: %s", 异常)
            # 非停止状态下等待退避时间后再重连
            if not self.停止事件.is_set():
                # 调用库方法：异步等待
                # 传入：退避秒数
                # 作用：延时后进入下一次连接尝试
                # 传出：无返回值
                await asyncio.sleep(退避秒数)
                退避秒数 = min(退避秒数 * 2, 60.0)

    # ─── 单次连接的消息循环 ───

    async def _运行连接(self, 连接) -> None:
        """处理单条连接：等待 hello 握手，然后进入接收循环并管理心跳任务。"""
        # 等待并校验 hello 握手包(s=1)，超时 6 秒视为连接失败
        try:
            # 调用库方法：接收下一条 ws 消息
            # 传入：无
            # 作用：阻塞等待服务器推送首帧握手结果
            # 传出：消息对象(含 type/data)
            首条消息 = await asyncio.wait_for(连接.receive(), timeout=6)
        except asyncio.TimeoutError:
            raise RuntimeError("等待网关 hello 握手包超时")
        # 解析首帧并处理握手结果(校验令牌/记录会话 id)
        首帧: dict[str, Any] = json.loads(首条消息.data)
        if 首帧.get("s") != 1:
            raise RuntimeError(f"网关首帧非握手包: {首帧}")
        await self._处理信令(连接, 首帧)
        # 创建本次连接的心跳任务
        self._心跳任务 = asyncio.create_task(self._心跳循环(连接))
        try:
            # 循环读取后续所有消息
            async for 消息 in 连接:
                if 消息.type == 2:  # aiohttp 消息类型 2 代表文本帧
                    try:
                        帧: dict[str, Any] = json.loads(消息.data)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    await self._处理信令(连接, 帧)
        finally:
            # 断开前取消心跳任务
            if self._心跳任务 is not None:
                self._心跳任务.cancel()
                try:
                    await self._心跳任务
                except asyncio.CancelledError:
                    pass
                self._心跳任务 = None

    async def _处理信令(self, 连接, 帧: dict[str, Any]) -> None:
        """按信令编号分发处理一条网关帧。返回: 无返回值。"""
        信令编号: int = int(帧.get("s", -1))
        if 信令编号 == 0:
            # 事件信令：取出事件字典与 sn，交给有序处理
            await self._处理事件帧(帧.get("d", {}), int(帧.get("sn", 0)))
        elif 信令编号 == 1:
            # hello 握手结果：检查是否鉴权成功
            握手结果: dict[str, Any] = 帧.get("d", {})
            if 握手结果.get("code") != 0:
                raise 令牌错误(f"网关握手失败: {握手结果}")
            self.会话ID = str(握手结果.get("session_id", ""))
        elif 信令编号 == 3:
            # pong：回应心跳
            self._pong事件.set()
        elif 信令编号 == 5:
            # reconnect：服务端要求断开重连，清空全部状态走全新会话
            _logger.warning("收到 reconnect 信令")
            raise _要求重连

    # ─── 心跳 ───

    async def _心跳循环(self, 连接) -> None:
        """每 30±5 秒发送一次 ping，6 秒内未收到 pong 则断开触发重连。"""
        while not self.停止事件.is_set():
            # 计算下一次心跳间隔(30±5 秒随机)
            间隔秒数: float = 30.0 + random.uniform(-5.0, 5.0)
            await asyncio.sleep(间隔秒数)
            if self.停止事件.is_set():
                break
            # 发送前清空 pong 信号，准备新一轮判定
            self._pong事件.clear()
            try:
                # 调用库方法：发送文本帧
                # 传入：ping JSON 文本(s=2, 携带当前已处理的最大 sn)
                # 作用：向服务器上报心跳并同步消息进度
                # 传出：无返回值
                await 连接.send_str(json.dumps({"s": 2, "sn": self.最大sn}))
                # 等待 pong，超过 6 秒判定心跳超时
                await asyncio.wait_for(self._pong事件.wait(), timeout=6)
            except asyncio.TimeoutError:
                _logger.warning("心跳 pong 超时，断开连接准备重连")
                try:
                    await 连接.close()
                except Exception:
                    pass
                return
            except Exception:
                return

    # ─── 事件帧有序处理 ───

    async def _处理事件帧(self, 事件数据: dict[str, Any], sn: int) -> None:
        """
        按 sn 有序处理事件：去重、乱序暂存、按序回调。
        参数:
            事件数据: 信令 s=0 的 d 字段。
            sn: 该事件的消息序号。
        返回:
            无返回值。
        """
        if sn <= self.最大sn:
            return  # 重复推送的旧 sn，直接丢弃
        # 不是期望的下一条，先暂存等待缺口补齐
        if sn != self.最大sn + 1:
            self.暂存区[sn] = 事件数据
            return
        # 顺序到达：更新进度并回调，随后尽可能消化暂存区
        self.最大sn = sn
        try:
            await self.事件处理器(事件数据)
        except Exception as 异常:
            _logger.exception("事件处理器异常: %s", 异常)
        # 从下一条开始连续消化暂存区中已补齐的事件
        while (self.最大sn + 1) in self.暂存区:
            下一条: dict[str, Any] = self.暂存区.pop(self.最大sn + 1)
            self.最大sn += 1
            try:
                await self.事件处理器(下一条)
            except Exception as 异常:
                _logger.exception("事件处理器异常: %s", 异常)
