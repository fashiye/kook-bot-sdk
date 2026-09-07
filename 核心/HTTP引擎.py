'''
KOOK HTTP 引擎模块：底层 REST 请求引擎，位于核心层。
只负责 aiohttp 会话、鉴权头、JSON 编解码与错误码处理，Bot/用户两种身份共用；
具体分类资源见 资源 层，由 资源/客户端.py 的 HTTP客户端 聚合装配。

参考文档: https://developer.kookapp.cn/doc/reference
'''
from typing import Any, Optional                         # 提供 Any/Optional 类型注解
import aiohttp                                           # 提供异步 HTTP 客户端，用于调用 KOOK REST 接口

from ..模型.错误 import 接口错误                           # 接口业务错误类型
from ..模型.常量 import 接口根地址                          # KOOK REST 接口根地址


class HTTP引擎:
    """KOOK REST 请求引擎：持有会话与鉴权令牌，统一负责请求发送与错误码解析。"""

    def __init__(self, 令牌: str, 鉴权前缀: str = "Bot"):
        """
        初始化引擎。
        参数:
            令牌: 访问令牌。机器人场景传 Bot 令牌；OAuth 用户场景传用户 access_token。
            鉴权前缀: Authorization 头的令牌前缀，Bot 用 "Bot"，用户令牌用 "Bearer"。
        """
        self.令牌 = 令牌
        # aiohttp 会话，启动时创建，负责所有 HTTP 请求的连接复用
        self.会话: Optional[aiohttp.ClientSession] = None
        # 鉴权请求头：按身份类型携带不同的令牌前缀
        self.请求头: dict[str, str] = {"Authorization": f"{鉴权前缀} {令牌}"}

    async def 打开(self) -> None:
        """创建 aiohttp 会话。返回: 无返回值。"""
        if self.会话 is None:
            # 调用库函数：创建异步 HTTP 会话
            # 传入：headers(默认请求头)，timeout 未指定(用库默认)
            # 作用：建立可复用的连接池，供后续所有 REST 请求使用
            # 传出：aiohttp.ClientSession 对象
            self.会话 = aiohttp.ClientSession(headers=self.请求头)

    async def 关闭(self) -> None:
        """关闭 aiohttp 会话并释放连接池。返回: 无返回值。"""
        if self.会话 is not None:
            # 调用库方法：关闭会话
            # 传入：无
            # 作用：优雅关闭所有底层连接
            # 传出：无返回值
            await self.会话.close()
            self.会话 = None

    async def 请求(self, 方法: str, 接口路径: str,
                   查询参数: Optional[dict[str, Any]] = None,
                   数据: Optional[dict[str, Any]] = None) -> Any:
        """
        发送一次 JSON REST 请求并返回 data 字段。
        参数:
            方法: HTTP 方法(GET/POST)。
            接口路径: 接口路径，如 "/message/create"。
            查询参数: URL 查询参数，GET 请求使用。
            数据: 请求体字典，POST 请求以 JSON 发送。
        返回:
            KOOK 响应的 data 字段。
        异常:
            RuntimeError: 会话未打开。
            接口错误: KOOK 返回 code 非 0。
        """
        if self.会话 is None:
            raise RuntimeError("HTTP 会话未打开，请先调用 打开()")
        # 拼接完整接口地址
        完整地址: str = f"{接口根地址}{接口路径}"
        # 调用库方法：发送 GET/POST 请求
        # 传入：method(方法), url(完整地址), params(查询参数), json(请求体自动转 JSON)
        # 作用：向 KOOK 服务器发起 HTTP 请求并等待响应
        # 传出：aiohttp.ClientResponse 对象
        响应 = await self.会话.request(method=方法, url=完整地址, params=查询参数, json=数据)
        return await self._解析响应(响应, 接口路径)

    async def 上传文件(self, 接口路径: str, 文件字段名: str,
                       文件字节: bytes, 文件名: str,
                       附加字段: Optional[dict[str, Any]] = None) -> Any:
        """
        以 multipart/form-data 上传文件(用于素材上传等接口)并返回 data 字段。
        参数:
            接口路径: 接口路径，如 "/asset/create"。
            文件字段名: 表单中文件字段名，KOOK 素材接口为 "file"。
            文件字节: 文件二进制内容。
            文件名: 上传时展示的文件名(需带扩展名以判定类型)。
            附加字段: 额外的普通表单字段，可选。
        返回:
            KOOK 响应的 data 字段。
        异常:
            RuntimeError: 会话未打开。
            接口错误: KOOK 返回 code 非 0。
        """
        if self.会话 is None:
            raise RuntimeError("HTTP 会话未打开，请先调用 打开()")
        # 构造 multipart 表单，文件字段与普通字段共用
        表单 = aiohttp.FormData()
        # 调用库方法：向表单追加文件
        # 传入：name(字段名), value(文件字节), filename(文件名)
        # 作用：以流式方式封装文件，发送时自动转 multipart 编码
        # 传出：无返回值(内部登记到表单)
        表单.add_field(文件字段名, 文件字节, filename=文件名)
        if 附加字段:
            for 字段名, 字段值 in 附加字段.items():
                # 调用库方法：向表单追加普通字段
                # 传入：name(字段名), value(字段值)
                # 作用：把普通参数一并编码进 multipart 表单
                # 传出：无返回值
                表单.add_field(字段名, str(字段值))
        # 拼接完整接口地址
        完整地址: str = f"{接口根地址}{接口路径}"
        # 调用库方法：发送 multipart POST 请求
        # 传入：url(完整地址), data(表单对象，自动设 Content-Type)
        # 作用：上传文件并等待响应
        # 传出：aiohttp.ClientResponse 对象
        响应 = await self.会话.post(完整地址, data=表单)
        return await self._解析响应(响应, 接口路径)

    async def _解析响应(self, 响应: aiohttp.ClientResponse, 接口路径: str) -> Any:
        """
        统一解析 KOOK 响应：读取 JSON 并检查业务状态码。
        参数:
            响应: aiohttp 响应对象。
            接口路径: 请求的接口路径，用于错误提示。
        返回:
            KOOK 响应的 data 字段。
        异常:
            接口错误: KOOK 返回 code 非 0。
        """
        # 调用库方法：读取 JSON 响应体
        # 传入：无
        # 作用：把响应体文本解析为字典
        # 传出：dict 响应结果
        结果字典: dict[str, Any] = await 响应.json()
        # 状态码 0 代表业务成功，否则抛出带错误码的异常
        if 结果字典.get("code") != 0:
            raise 接口错误(int(结果字典.get("code", -1)), str(结果字典.get("message", "")), 接口路径)
        return 结果字典.get("data")
