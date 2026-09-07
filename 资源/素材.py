'''
KOOK 素材资源模块：封装媒体文件上传(asset) REST 接口。
参考文档: https://developer.kookapp.cn/doc/http/asset
'''
from typing import Any                      # 提供 Any 类型注解(上传返回 data)

from ..核心.资源基座 import 资源基类                   # 资源基类


class 素材资源(资源基类):
    """素材分类资源：上传图片/视频/文件以换取 KOOK 站内资源地址(发消息前需先上传)。"""

    async def 上传(self, 文件字节: bytes, 文件名: str) -> Any:
        """
        上传媒体文件(multipart，支持图片、.mp4/.mov 视频与任意文件)。
        参数:
            文件字节: 文件二进制内容。
            文件名: 文件名(需带扩展名，服务端据此判定资源类型)。
        返回:
            data 字典，含 url(资源地址)，可直接作为图片/视频/文件消息的 content。
        """
        # 素材接口的文件表单字段固定为 file
        return await self._上传文件("/asset/create", "file", 文件字节, 文件名)
