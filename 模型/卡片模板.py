'''
KOOK 卡片模板库模块：基于 卡片 类预置常用卡片消息模板(状态提示/确认/选项/用户信息等)。
所有模板函数返回可直接发送的卡片消息数组(list[dict])，内容符合官方卡片结构。
'''
from typing import Any, Optional                       # 提供 Any/Optional 类型注解

from .卡片 import 卡片, 创建按钮元素, 构建卡片消息        # 卡片构建基元与消息组装


# 状态名 → (卡片主题, 边框颜色) 映射，同时兼容中英文状态名
状态样式表: dict[str, tuple[str, str]] = {
    "成功": ("success", "#00D26A"), "success": ("success", "#00D26A"),
    "错误": ("danger", "#F54A45"), "danger": ("danger", "#F54A45"),
    "警告": ("warning", "#FFAA00"), "warning": ("warning", "#FFAA00"),
    "信息": ("primary", "#3370FF"), "info": ("primary", "#3370FF"),
}


def 状态卡片(标题: str, 说明: str = "", 状态: str = "信息",
             备注: str = "") -> list[dict[str, Any]]:
    """
    生成带状态色标题的提示卡片(标题 + 正文 + 可选小字备注)。
    参数:
        标题: 卡片主标题(≤100 字符)。
        说明: 正文(≤2000 字符)，空则不渲染正文模块。
        状态: 状态样式，成功/错误/警告/信息(也接受 success/danger/warning/info)。
        备注: 底部小字备注(≤2000 字符)，空则省略。
    返回:
        单卡片消息数组。
    异常:
        ValueError: 状态名不受支持。
    """
    样式 = 状态样式表.get(状态)
    if 样式 is None:
        raise ValueError(f"状态只能为 {'、'.join(状态样式表)}")
    主题, 颜色 = 样式
    卡 = 卡片(颜色=颜色, 主题=主题)
    卡.添加标题模块(标题)
    if 说明:
        卡.添加内容模块(说明)
    if 备注:
        # 备注使用纯文本小字元素
        卡.添加备注模块([{"type": "plain-text", "content": 备注}])
    return 构建卡片消息([卡])


def 确认卡片(标题: str, 说明: str = "", 确认文本: str = "确认",
             确认值: str = "confirm", 取消文本: str = "取消", 取消值: str = "cancel",
             颜色: str = "#3370FF") -> list[dict[str, Any]]:
    """
    生成"确认/取消"双按钮交互卡片，供按钮点击事件或 等待按钮点击 使用。
    参数:
        标题: 卡片标题。
        说明: 正文，可空。
        确认文本/确认值: 确认按钮文字与回传 value。
        取消文本/取消值: 取消按钮文字与回传 value。
        颜色: 卡片边框颜色。
    返回:
        单卡片消息数组。
    """
    卡 = 卡片(颜色=颜色)
    卡.添加标题模块(标题)
    if 说明:
        卡.添加内容模块(说明)
    卡.添加交互模块([创建按钮元素(确认文本, 确认值, "return-val"),
                       创建按钮元素(取消文本, 取消值, "return-val")])
    return 构建卡片消息([卡])


def 选项卡片(标题: str, 选项列表: list[tuple[str, str]], 说明: str = "",
             颜色: str = "#3370FF") -> list[dict[str, Any]]:
    """
    生成多项选择按钮卡片(按钮最多 4 个)。
    参数:
        标题: 卡片标题。
        选项列表: (按钮文字, 回传 value) 二元组列表，1-4 项。
        说明: 引导正文，可空。
        颜色: 卡片边框颜色。
    返回:
        单卡片消息数组。
    异常:
        ValueError: 选项数量不在 1-4。
    """
    按钮列表: list[dict[str, Any]] = [创建按钮元素(文本, 值, "return-val")
                                        for 文本, 值 in 选项列表]
    卡 = 卡片(颜色=颜色)
    卡.添加标题模块(标题)
    if 说明:
        卡.添加内容模块(说明)
    卡.添加交互模块(按钮列表)
    return 构建卡片消息([卡])


def 用户信息卡片(用户: dict[str, Any], 附加说明: str = "",
                 ) -> list[dict[str, Any]]:
    """
    把 KOOK 用户字典渲染为信息卡片(头像 + 昵称/用户名 + 附加说明)。
    参数:
        用户: 用户信息字典(user/view、user/me 或事件作者等返回)。
        附加说明: 额外展示文本(KMD 语法)，可空。
    返回:
        单卡片消息数组。
    """
    昵称: str = str(用户.get("nickname") or 用户.get("username") or "")
    全名: str = str(用户.get("username") or "")
    编号: str = str(用户.get("identify_num") or "")
    头像: str = str(用户.get("avatar") or "")
    用户身份标签: str = f"{全名}#{编号}" if 编号 else 全名
    # 拼接说明行：昵称 → 用户名#编号 → 自定义说明
    正文行: str = f"**{昵称}**\n(met){用户.get('id', '')}(met)\n`{用户身份标签}`"
    卡 = 卡片()
    卡.添加标题模块("用户信息")
    卡.添加内容模块(正文行, "kmarkdown",
                      {"type": "image", "src": 头像, "alt": "头像", "size": "lg", "circle": True} if 头像 else None)
    if 附加说明:
        卡.添加备注模块([{"type": "kmarkdown", "content": 附加说明}])
    return 构建卡片消息([卡])
