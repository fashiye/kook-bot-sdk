'''
KOOK 私信资源模块：封装私信聊天消息(direct-message)与私聊会话(user-chat)两组 REST 接口。
参考文档:
- https://developer.kookapp.cn/doc/http/direct-message
- https://developer.kookapp.cn/doc/http/user-chat
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类, 整理发送内容       # 资源基类与消息内容整理工具


class 私信消息资源(资源基类):
    """私信消息分类资源：向用户私信收发消息，与频道消息结构类似但归属独立接口。"""

    async def 获取列表(self, 会话码: Optional[str] = None, 目标用户ID: Optional[str] = None,
                        参考消息ID: Optional[str] = None, 查询模式: Optional[str] = None,
                        页码: int = 1, 页大小: int = 50) -> Any:
        """
        获取某个私信会话的消息列表。
        参数:
            会话码: 私信会话 Code(chat_code)，与 目标用户ID 至少填一个。
            目标用户ID: 目标用户 id，传了后端自动创建会话，可不传会话码。
            参考消息ID: 翻页参考消息 id，不传查询最新消息。
            查询模式: "before"/"around"/"after"，围绕参考消息的方向。
            页码: 目标页数。
            页大小: 单页条数，默认 50。
        返回:
            含 items(消息列表) 的 data 字典。
        """
        查询: dict[str, Any] = {"page": 页码, "page_size": 页大小}
        if 会话码:
            查询["chat_code"] = 会话码
        if 目标用户ID:
            查询["target_id"] = 目标用户ID
        if 参考消息ID:
            查询["msg_id"] = 参考消息ID
        if 查询模式:
            查询["flag"] = 查询模式
        return await self._请求("GET", "/direct-message/list", 查询参数=查询)

    async def 获取详情(self, 会话码: str, 消息ID: str) -> Any:
        """
        获取私信聊天消息详情。
        参数:
            会话码: 消息所在私信会话 Code。
            消息ID: 私信消息 id。
        返回:
            消息详情字典。
        """
        return await self._请求("GET", "/direct-message/view",
                                查询参数={"chat_code": 会话码, "msg_id": 消息ID})

    async def 发送(self, 内容: str | list | dict, 目标用户ID: Optional[str] = None,
                    会话码: Optional[str] = None, 类型: Optional[int] = None,
                    引用消息ID: Optional[str] = None, 随机串: Optional[str] = None,
                    模板ID: Optional[str] = None, 回复消息ID: Optional[str] = None) -> Any:
        """
        向用户发送私信(缺省自动创建会话)。
        参数:
            内容: 文本或卡片结构。
            目标用户ID: 目标用户 id，与 会话码 至少填一个。
            会话码: 既有私信会话 Code。
            类型: 消息类型，默认自动：文本按 9(KMD)，卡片结构按 10。
            引用消息ID: 回复的源消息 id。
            随机串: nonce，服务端原样返回。
            模板ID: 模板消息 id。
            回复消息ID: 5 分钟内用户刚发给本机器人的消息 id(可降配额)。
        返回:
            data 字典，含 msg_id。
        """
        消息类型值, 内容文本 = 整理发送内容(内容, 类型)
        发送数据: dict[str, Any] = {"type": 消息类型值, "content": 内容文本}
        if 目标用户ID:
            发送数据["target_id"] = 目标用户ID
        if 会话码:
            发送数据["chat_code"] = 会话码
        if 引用消息ID:
            发送数据["quote"] = 引用消息ID
        if 随机串:
            发送数据["nonce"] = 随机串
        if 模板ID:
            发送数据["template_id"] = 模板ID
        if 回复消息ID:
            发送数据["reply_msg_id"] = 回复消息ID
        return await self._请求("POST", "/direct-message/create", 数据=发送数据)

    async def 编辑(self, 消息ID: str, 新内容: str | list | dict,
                    引用消息ID: Optional[str] = None, 模板ID: Optional[str] = None,
                    回复消息ID: Optional[str] = None) -> None:
        """
        更新已发送的私信消息(仅支持 KMD 与卡片消息)。
        参数:
            消息ID: 待编辑私信消息 id。
            新内容: 新文本或新卡片结构。
            引用消息ID: 传 id 覆盖回复；传空串删除回复；None 不改变。
            模板ID: 模板消息 id。
            回复消息ID: 见发送的同名参数。
        返回:
            无返回值。
        """
        _, 内容文本 = 整理发送内容(新内容)
        更新数据: dict[str, Any] = {"msg_id": 消息ID, "content": 内容文本}
        if 引用消息ID is not None:
            更新数据["quote"] = 引用消息ID
        if 模板ID:
            更新数据["template_id"] = 模板ID
        if 回复消息ID:
            更新数据["reply_msg_id"] = 回复消息ID
        await self._请求("POST", "/direct-message/update", 数据=更新数据)

    async def 删除(self, 消息ID: str) -> None:
        """
        删除已发送的私信消息(只能删自己的)。
        参数:
            消息ID: 待删除私信消息 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/direct-message/delete", 数据={"msg_id": 消息ID})

    async def 回应用户列表(self, 消息ID: str, 表情: str) -> Any:
        """
        获取私信消息上点了某回应的用户列表。
        参数:
            消息ID: 私信消息 id。
            表情: 表情标识(会自动 URL 编码)。
        返回:
            用户字典列表。
        """
        return await self._请求("GET", "/direct-message/reaction-list",
                                查询参数={"msg_id": 消息ID, "emoji": 表情})

    async def 添加回应(self, 消息ID: str, 表情: str) -> None:
        """
        给私信消息添加回应。
        参数:
            消息ID: 私信消息 id。
            表情: 表情标识。
        返回:
            无返回值。
        """
        await self._请求("POST", "/direct-message/add-reaction", 数据={"msg_id": 消息ID, "emoji": 表情})

    async def 删除回应(self, 消息ID: str, 表情: str, 用户ID: Optional[str] = None) -> None:
        """
        删除私信消息上的某个回应。
        参数:
            消息ID: 私信消息 id。
            表情: 表情标识。
            用户ID: 删除他人回应时的用户 id，缺省删除自己的。
        返回:
            无返回值。
        """
        删除数据: dict[str, Any] = {"msg_id": 消息ID, "emoji": 表情}
        if 用户ID:
            删除数据["user_id"] = 用户ID
        await self._请求("POST", "/direct-message/delete-reaction", 数据=删除数据)


class 私信会话资源(资源基类):
    """私聊会话分类资源：管理机器人与用户之间的一对一私聊会话。"""

    async def 获取列表(self, 页码: int = 1, 页大小: int = 50,
                        合并全部分页: bool = False) -> Any:
        """
        获取私信聊天会话列表。
        参数:
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items(会话列表) 与 meta(分页信息) 的 data 字典；开启合并全部分页时返回列表。
        """
        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            return await self._请求("GET", "/user-chat/list",
                                    查询参数={"page": 页, "page_size": 每页})

        if 合并全部分页:
            return await self._合并分页(取一页)
        return await self._请求("GET", "/user-chat/list",
                                查询参数={"page": 页码, "page_size": 页大小})

    async def 获取详情(self, 会话码: str) -> Any:
        """
        获取私信聊天会话详情。
        参数:
            会话码: 私信会话 Code。
        返回:
            会话详情字典(含未读数/是否好友/是否屏蔽/对方信息等)。
        """
        return await self._请求("GET", "/user-chat/view", 查询参数={"chat_code": 会话码})

    async def 创建(self, 目标用户ID: str) -> Any:
        """
        与指定用户建立私信会话。
        参数:
            目标用户ID: 目标用户 id。
        返回:
            新会话详情字典(含 code)。
        """
        return await self._请求("POST", "/user-chat/create", 数据={"target_id": 目标用户ID})

    async def 删除(self, 会话码: str) -> None:
        """
        删除自己的私信会话。
        参数:
            会话码: 目标私信会话 Code。
        返回:
            无返回值。
        """
        await self._请求("POST", "/user-chat/delete", 数据={"chat_code": 会话码})
