'''
KOOK 服务器表情资源模块：封装服务器自定义表情(guild-emoji)的增删改查 REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/guild-emoji
'''
from typing import Any, Optional                      # 提供 Any/Optional 类型注解

from ...核心.资源基座 import 资源基类                     # 资源基类


class 服务器表情资源(资源基类):
    """服务器表情分类资源：自定义表情需 PNG 格式、不超过 256KB。"""

    async def 获取列表(self, 服务器ID: str, 页码: int = 1, 页大小: int = 50,
                        合并全部分页: bool = False) -> Any:
        """
        获取服务器自定义表情列表。
        参数:
            服务器ID: 服务器 id。
            页码: 目标页数。
            页大小: 每页数据数量。
            合并全部分页: True 时自动翻页并把全量条目合并成一个列表返回。
        返回:
            含 items(表情列表) 与 meta 的 data 字典，表情含 name/id/user_info；开启合并全部分页时返回列表。
        """
        固定查询: dict[str, Any] = {"guild_id": 服务器ID}

        async def 取一页(页: int, 每页: int) -> dict[str, Any]:
            # 单页请求(供自动翻页回调使用)
            页查询: dict[str, Any] = dict(固定查询)
            页查询.update({"page": 页, "page_size": 每页})
            return await self._请求("GET", "/guild-emoji/list", 查询参数=页查询)

        if 合并全部分页:
            return await self._合并分页(取一页)
        查询: dict[str, Any] = dict(固定查询)
        查询.update({"page": 页码, "page_size": 页大小})
        return await self._请求("GET", "/guild-emoji/list", 查询参数=查询)

    async def 创建(self, 服务器ID: str, 文件字节: bytes, 文件名: str,
                    名称: Optional[str] = None) -> Any:
        """
        上传并创建服务器自定义表情(multipart，PNG 且 ≤256KB)。
        参数:
            服务器ID: 服务器 id。
            文件字节: PNG 图片二进制内容。
            文件名: 图片文件名(需带 .png 扩展名)。
            名称: 表情名(2-32 字符)；None 由服务端生成随机名。
        返回:
            新表情字典(含 name/id)。
        """
        附加字段: dict[str, Any] = {"guild_id": 服务器ID}
        if 名称 is not None:
            附加字段["name"] = 名称
        return await self._上传文件("/guild-emoji/create", "emoji", 文件字节, 文件名, 附加字段)

    async def 更新(self, 表情ID: str, 名称: str) -> None:
        """
        重命名服务器自定义表情。
        参数:
            表情ID: 待更新表情 id。
            名称: 新表情名(2-32 字符)。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild-emoji/update", 数据={"id": 表情ID, "name": 名称})

    async def 删除(self, 表情ID: str) -> None:
        """
        删除服务器自定义表情。
        参数:
            表情ID: 待删除表情 id。
        返回:
            无返回值。
        """
        await self._请求("POST", "/guild-emoji/delete", 数据={"id": 表情ID})
