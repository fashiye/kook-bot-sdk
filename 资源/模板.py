'''
KOOK 消息模板资源模块：封装消息模板(template)的增删改查 REST 接口。
模板用于固定格式消息，可显著降低限流影响。参考文档: https://developer.kookapp.cn/doc/http/template
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ..核心.资源基座 import 资源基类                       # 资源基类


class 模板资源(资源基类):
    """消息模板分类资源：模板以 twig 语法书写，content 即模板正文。"""

    async def 获取列表(self) -> Any:
        """
        获取当前机器人的全部消息模板。
        返回:
            含 items(模板列表) 的 data 字典。
        """
        return await self._请求("GET", "/template/list")

    async def 创建(self, 标题: str, 内容: str, 渲染类型: int = 0,
                    消息格式: int = 1, 测试数据: Optional[str] = None,
                    测试频道: Optional[str] = None) -> Any:
        """
        创建消息模板。
        参数:
            标题: 模板标题，必传。
            内容: twig 模板正文，必传。
            渲染类型: 渲染引擎类型，目前固定 0(twig)。
            消息格式: 1 kmd 消息 / 2 json 卡片 / 3 yaml 卡片。
            测试数据: 控制台测试用的样例输入 JSON 文本，可选。
            测试频道: 控制台测试用的频道 id，可选。
        返回:
            data 字典，含 model(新模板，含 id)。
        """
        创建数据: dict[str, Any] = {"title": 标题, "content": 内容,
                                     "type": 渲染类型, "msgtype": 消息格式}
        if 测试数据:
            创建数据["test_data"] = 测试数据
        if 测试频道:
            创建数据["test_channel"] = 测试频道
        return await self._请求("POST", "/template/create", 数据=创建数据)

    async def 更新(self, 模板ID: str, 标题: Optional[str] = None,
                    内容: Optional[str] = None, 渲染类型: Optional[int] = None,
                    消息格式: Optional[int] = None, 测试数据: Optional[str] = None,
                    测试频道: Optional[str] = None) -> Any:
        """
        更新消息模板(按需传参)。
        参数:
            模板ID: 目标模板 id，必传。
            标题: 新标题。
            内容: 新模板正文。
            渲染类型: 渲染引擎类型(0=twig)。
            消息格式: 1 kmd / 2 json 卡片 / 3 yaml 卡片。
            测试数据: 测试样例输入。
            测试频道: 测试频道 id。
        返回:
            data 字典，含 model(更新后的模板)。
        """
        更新数据: dict[str, Any] = {"id": 模板ID}
        if 标题 is not None:
            更新数据["title"] = 标题
        if 内容 is not None:
            更新数据["content"] = 内容
        if 渲染类型 is not None:
            更新数据["type"] = 渲染类型
        if 消息格式 is not None:
            更新数据["msgtype"] = 消息格式
        if 测试数据 is not None:
            更新数据["test_data"] = 测试数据
        if 测试频道 is not None:
            更新数据["test_channel"] = 测试频道
        return await self._请求("POST", "/template/update", 数据=更新数据)

    async def 删除(self, 模板ID: str) -> None:
        """
        删除消息模板(删除后使用该模板的消息将无法发送)。
        参数:
            模板ID: 目标模板 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/template/delete", 数据={"id": 模板ID})
