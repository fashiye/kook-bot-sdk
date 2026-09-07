'''
KOOK 频道消息资源模块：封装频道聊天消息相关 REST 接口(获取/发送/编辑/删除/回应/置顶/管道)。
参考文档: https://developer.kookapp.cn/doc/http/message
'''
from typing import Any, Optional                            # 提供 Any/Optional 类型注解
import aiohttp                                              # 提供异步 HTTP 客户端，管道消息用独立连接发送

from ...核心.资源基座 import 资源基类, 整理发送内容           # 资源基类与消息内容整理工具
from ...模型.错误 import 接口错误                             # 接口业务错误类型
from ...模型.常量 import 接口根地址                           # KOOK REST 接口根地址(管道消息独立请求用)


class 频道消息资源(资源基类):
    """频道消息分类资源：一条消息 ID 通常指频道消息。"""

    async def 获取列表(self, 频道ID: str, 参考消息ID: Optional[str] = None,
                        仅置顶: Optional[bool] = None, 查询模式: Optional[str] = None,
                        页大小: int = 50) -> Any:
        """
        获取频道聊天消息列表(以参考消息为中心的前后翻页)。
        参数:
            频道ID: 目标频道 id。
            参考消息ID: 翻页参考消息 id，不传则查询最新消息。
            仅置顶: True 只查置顶消息(只能查最新一条)；False/None 查普通消息。
            查询模式: "before"/"around"/"after"，围绕参考消息的方向，不传默认最新。
            页大小: 单页条数，默认 50。
        返回:
            含 items(消息列表) 的 data 字典。
        """
        查询: dict[str, Any] = {"target_id": 频道ID, "page_size": 页大小}
        if 参考消息ID:
            查询["msg_id"] = 参考消息ID
        if 仅置顶 is not None:
            查询["pin"] = 1 if 仅置顶 else 0
        if 查询模式:
            查询["flag"] = 查询模式
        return await self._请求("GET", "/message/list", 查询参数=查询)

    async def 获取详情(self, 消息ID: str) -> Any:
        """
        获取频道聊天消息详情。
        参数:
            消息ID: 待查询消息 id。
        返回:
            消息详情字典。
        """
        return await self._请求("GET", "/message/view", 查询参数={"msg_id": 消息ID})

    async def 发送(self, 频道ID: str, 内容: str | list | dict,
                    类型: Optional[int] = None, 引用消息ID: Optional[str] = None,
                    随机串: Optional[str] = None, 临时用户ID: Optional[str] = None,
                    模板ID: Optional[str] = None, 回复消息ID: Optional[str] = None) -> Any:
        """
        向频道发送文本或卡片消息。
        参数:
            频道ID: 目标频道 id。
            内容: 文本，或卡片数组/字典(自动按 type=10 发送)。
            类型: 消息类型，默认自动：文本按 9(KMD)，卡片结构按 10。
            引用消息ID: 回复的源消息 id。
            随机串: nonce，服务端原样返回，用于幂等与对账。
            临时用户ID: 传该用户 id 则发临时消息(不入库，仅该用户在频道内可见)。
            模板ID: 使用消息模板时的模板 id，content 作为模板输入。
            回复消息ID: 5 分钟内用户刚发的消息 id，首次回复可降低配额消耗。
        返回:
            data 字典，含 msg_id/msg_timestamp/nonce。
        """
        消息类型值, 内容文本 = 整理发送内容(内容, 类型)
        发送数据: dict[str, Any] = {"target_id": 频道ID, "type": 消息类型值, "content": 内容文本}
        if 引用消息ID:
            发送数据["quote"] = 引用消息ID
        if 随机串:
            发送数据["nonce"] = 随机串
        if 临时用户ID:
            发送数据["temp_target_id"] = 临时用户ID
        if 模板ID:
            发送数据["template_id"] = 模板ID
        if 回复消息ID:
            发送数据["reply_msg_id"] = 回复消息ID
        return await self._请求("POST", "/message/create", 数据=发送数据)

    async def 编辑(self, 消息ID: str, 新内容: str | list | dict,
                    引用消息ID: Optional[str] = None, 临时用户ID: Optional[str] = None,
                    模板ID: Optional[str] = None, 回复消息ID: Optional[str] = None) -> None:
        """
        更新频道消息(仅支持 KMD 与卡片消息)。
        参数:
            消息ID: 待编辑消息 id。
            新内容: 新文本或新卡片结构。
            引用消息ID: 传 id 覆盖回复关系；传空串删除回复；None 不改变。
            临时用户ID: 针对特定用户的临时更新(原消息必须是正常消息)。
            模板ID: 模板消息 id。
            回复消息ID: 见发送的同名参数。
        返回:
            无返回值。
        """
        _, 内容文本 = 整理发送内容(新内容)
        更新数据: dict[str, Any] = {"msg_id": 消息ID, "content": 内容文本}
        if 引用消息ID is not None:
            更新数据["quote"] = 引用消息ID
        if 临时用户ID:
            更新数据["temp_target_id"] = 临时用户ID
        if 模板ID:
            更新数据["template_id"] = 模板ID
        if 回复消息ID:
            更新数据["reply_msg_id"] = 回复消息ID
        await self._请求("POST", "/message/update", 数据=更新数据)

    async def 删除(self, 消息ID: str) -> None:
        """
        删除频道消息(机器人需有对应权限)。
        参数:
            消息ID: 待删除消息 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/message/delete", 数据={"msg_id": 消息ID})

    async def 回应用户列表(self, 消息ID: str, 表情: str) -> Any:
        """
        获取频道消息上点了某回应的用户列表。
        参数:
            消息ID: 频道消息 id。
            表情: 表情标识，可为服务器表情或标准 emoji(会经 URL 编码)。
        返回:
            用户字典列表。
        """
        # 表情含特殊字符，交给 aiohttp 自动做 URL 编码
        return await self._请求("GET", "/message/reaction-list",
                                查询参数={"msg_id": 消息ID, "emoji": 表情})

    async def 添加回应(self, 消息ID: str, 表情: str) -> None:
        """
        给频道消息添加一个回应表情。
        参数:
            消息ID: 频道消息 id。
            表情: 表情标识，可为服务器表情或标准 emoji。
        返回:
            无返回值。
        """
        await self._请求("POST", "/message/add-reaction", 数据={"msg_id": 消息ID, "emoji": 表情})

    async def 删除回应(self, 消息ID: str, 表情: str, 用户ID: Optional[str] = None) -> None:
        """
        删除频道消息上的某个回应。
        参数:
            消息ID: 频道消息 id。
            表情: 表情标识。
            用户ID: 删除他人回应时的目标用户 id，缺省删除自己的回应(需管理消息权限)。
        返回:
            无返回值。
        """
        删除数据: dict[str, Any] = {"msg_id": 消息ID, "emoji": 表情}
        if 用户ID:
            删除数据["user_id"] = 用户ID
        await self._请求("POST", "/message/delete-reaction", 数据=删除数据)

    async def 置顶(self, 消息ID: str, 频道ID: str) -> None:
        """
        置顶频道消息(需管理消息权限)。
        参数:
            消息ID: 待置顶消息 id。
            频道ID: 消息所在频道 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/message/pin", 数据={"msg_id": 消息ID, "target_id": 频道ID})

    async def 取消置顶(self, 消息ID: str, 频道ID: str) -> None:
        """
        取消置顶频道消息(需管理消息权限)。
        参数:
            消息ID: 待取消置顶消息 id。
            频道ID: 消息所在频道 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/message/unpin", 数据={"msg_id": 消息ID, "target_id": 频道ID})


async def 发送管道消息(访问令牌: str, 内容: str | list | dict,
                       类型: Optional[int] = None, 频道ID: Optional[str] = None,
                       模板输入: Optional[dict[str, Any]] = None) -> Any:
    """
    通过消息管道向频道发送消息(需先在开发者后台创建入管道并取得 access_token)。
    与机器人令牌无关，使用独立连接、不带 Authorization 头，故作为模块级函数提供。
    参数:
        访问令牌: 消息管道的 access_token。
        内容: 文本或卡片结构；未使用模板时发送内容。
        类型: 消息类型；未填且无模板时默认 KMD。
        频道ID: 目标文字频道 id(须与管道同一服务器)，不填按管道默认设置。
        模板输入: 使用模板时传入的模板变量字典(此时忽略 内容/类型)。
    返回:
        data 字典，含 msg_id。
    异常:
        接口错误: KOOK 返回 code 非 0。
    """
    # 拼查询参数：管道鉴权令牌与发送选项
    查询参数: dict[str, Any] = {"access_token": 访问令牌}
    if 类型 is not None:
        查询参数["type"] = 类型
    if 频道ID:
        查询参数["target_id"] = 频道ID
    # POST 体：有模板时直接传模板变量，否则包一层 content
    请求体: Any = 模板输入 if 模板输入 is not None else {"content": 整理发送内容(内容)[1]}
    完整地址: str = f"{接口根地址}/message/send-pipemsg"
    # 调用库函数：创建独立异步 HTTP 会话
    # 传入：无参数(默认请求头)
    # 作用：管道消息不经机器人令牌，需自带连接发送
    # 传出：aiohttp.ClientSession 对象
    async with aiohttp.ClientSession() as 临时会话:
        # 调用库方法：发送 POST 请求
        # 传入：url(完整地址), params(查询参数), json(请求体)
        # 作用：把消息投递到管道目标频道
        # 传出：aiohttp.ClientResponse 对象
        响应 = await 临时会话.post(完整地址, params=查询参数, json=请求体)
        # 调用库方法：读取 JSON 响应体
        # 传入：无
        # 作用：解析服务端返回结果
        # 传出：dict 响应结果
        结果字典: dict[str, Any] = await 响应.json()
    # 业务状态码非 0 时抛错，保持与库内一致
    if 结果字典.get("code") != 0:
        raise 接口错误(int(结果字典.get("code", -1)), str(结果字典.get("message", "")), "/message/send-pipemsg")
    return 结果字典.get("data")
