# -*- coding: utf-8 -*-
'''
KOOK Bot SDK 示例：快速演示 启动钩子 / 命令路由 / 按钮点击 / 卡片 / 等待回复。
运行前请把下方令牌与目标频道填入，或在环境变量 KOOK_TOKEN 中提供令牌。
'''
import os                          # 读取环境变量令牌
from kook库 import 机器人, 卡片, 创建按钮元素, 构建卡片消息   # 主类与卡片构建工具

# 从环境变量读取令牌，避免密钥硬编码进源码
令牌: str = os.environ.get("KOOK_TOKEN", "你的机器人令牌")
机器人实例 = 机器人(令牌)


@机器人实例.启动时
async def 上线通知(机器人对象) -> None:
    """启动后打印日志并给指定频道发送问候。"""
    print("机器人已上线")
    频道ID: str = os.environ.get("KOOK_CHANNEL_ID", "")
    if 频道ID:
        await 机器人对象.发送频道(频道ID, "示例机器人已上线 ✅")


@机器人实例.命令("!ping")
async def 响应Ping(事件, 参数: str) -> None:
    """命令路由：!ping → 引用回复 pong。"""
    await 事件.引用回复(f"pong!(参数: {参数})")


@机器人实例.命令("!卡片")
async def 发卡片(事件, 参数: str) -> None:
    """命令路由：!卡片 → 发送带按钮的链式卡片。"""
    按钮 = 创建按钮元素("点我", "demo_button", "return-val")
    卡 = (卡片().添加标题模块("示例卡片")
          .添加内容模块("这是一张由库链式 API 生成的卡片")
          .添加分割线模块()
          .添加交互模块([按钮]))
    await 事件.回复(构建卡片消息([卡]))


@机器人实例.按钮点击
async def 处理按钮(事件) -> None:
    """按钮点击系统事件：按回传 value 分支处理。"""
    if str(事件.主体.get("value")) == "demo_button":
        await 事件.回复("按钮被点击啦！")
        await 事件.私信作者("偷偷告诉你，你的用户 ID 是 " + 事件.作者ID)


if __name__ == "__main__":
    机器人实例.运行()
