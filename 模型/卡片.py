'''
KOOK 基础卡片消息类：按官方卡片消息文档手工构建原生 JSON 结构，不依赖第三方 SDK。
卡片的所有"添加…"方法返回自身(self)，支持链式调用，例如:
    卡 = 卡片().添加标题模块("标题").添加内容模块("正文").添加交互模块([...])
参考文档: https://developer.kookapp.cn/doc/cardmessage
'''
from typing import Any, Callable, Optional                # 提供类型注解 Any/Callable/Optional
import json                                              # 提供 JSON 序列化，用于把卡片消息转成可发送的字符串

from .按钮绑定 import 按钮回调中心                          # 按钮回调中心，供"创建即绑定回调"语法糖登记


# 卡片/按钮主题合法取值集合，theme 为 none/invisible 时不渲染边框，取自官方文档
卡片主题集合: frozenset[str] = frozenset({"primary", "success", "danger", "warning", "info", "secondary", "none", "invisible"})
# 卡片尺寸合法取值集合，官方目前仅支持 sm 与 lg；lg 仅在 PC 端有效，移动端一律按 sm 显示
卡片尺寸集合: frozenset[str] = frozenset({"sm", "lg"})


def 创建纯文本元素(内容: str, 转换表情: bool = True) -> dict[str, Any]:
    """
    构造 plain-text 纯文本元素字典。
    参数:
        内容: 纯文本内容，最大 2000 个字符。
        转换表情: 是否把 emoji shortcut 转为真正的 emoji，默认 True。
    返回:
        纯文本元素字典，可直接放进模块的 text/elements/fields 字段。
    异常:
        ValueError: 内容为空或超过 2000 个字符。
    """
    if not 内容 or len(内容) > 2000:
        raise ValueError("纯文本内容不能为空且不能超过 2000 个字符")
    return {"type": "plain-text", "content": 内容, "emoji": 转换表情}


def 创建KMD元素(内容: str) -> dict[str, Any]:
    """
    构造 kmarkdown 富文本元素字典。
    参数:
        内容: KMarkdown 语法文本，最大 5000 个字符。
    返回:
        KMD 元素字典，可直接放进模块的 text/elements/fields 字段。
    异常:
        ValueError: 内容为空或超过 5000 个字符。
    """
    if not 内容 or len(内容) > 5000:
        raise ValueError("KMD 文本内容不能为空且不能超过 5000 个字符")
    return {"type": "kmarkdown", "content": 内容}


def 创建图片元素(图片地址: str, 替代文字: str = "", 尺寸: str = "lg", 圆形: bool = False, 备用地址: str = "") -> dict[str, Any]:
    """
    构造 image 图片元素字典。
    参数:
        图片地址: 图片 URL，推荐先经 asset 接口上传转存得到 KOOK 链接。
        替代文字: 图片无法加载时显示的替代文字。
        尺寸: 图片大小，仅图文混排时生效，只能取 sm 或 lg。
        圆形: 是否裁剪为圆形。
        备用地址: 外链转存失败时使用的兜底图片地址。
    返回:
        图片元素字典，用于 image-group、container、context 等模块。
    异常:
        ValueError: 图片地址为空或尺寸不合法。
    """
    if not 图片地址:
        raise ValueError("图片地址不能为空")
    if 尺寸 not in 卡片尺寸集合:
        raise ValueError(f"图片尺寸只能为 {'、'.join(卡片尺寸集合)}")
    # 图片元素基础字典，备用地址仅在填写时才写入，避免服务端误判
    图片元素: dict[str, Any] = {"type": "image", "src": 图片地址, "alt": 替代文字, "size": 尺寸, "circle": 圆形}
    if 备用地址:
        图片元素["fallbackUrl"] = 备用地址
    return 图片元素


def 创建按钮元素(文本: str, 值: str = "", 点击类型: str = "", 主题: str = "primary", 文本类型: str = "plain-text",
                回调: Optional[Callable] = None) -> dict[str, Any]:
    """
    构造 button 按钮交互元素字典；可传入 回调 实现"创建即绑定"，点击后自动触发(见说明)。
    参数:
        文本: 按钮上显示的文字。
        值: 点击后回调/跳转携带的字符串值。
        点击类型: 空串为无事件；"link" 跳转到值代表的链接；"return-val" 通过按钮点击事件把值回传。
        主题: 按钮主题色，取值见卡片主题集合。
        文本类型: 按钮文字格式，只能取 plain-text 或 kmarkdown。
        回调: 可选。绑定按钮点击的处理函数，签名 async def 处理(事件) 或 def 处理(事件)，
              收到点击时被机器人自动调用(事件.主体含 value/user_id 等)；点击类型将自动置为 return-val。
    返回:
        按钮元素字典，只能放入 action-group 模块的 elements 列表。
    异常:
        ValueError: 文本为空、点击类型/文本类型不合法、绑定回调但缺值，或 link 按钮绑定回调。
    """
    if not 文本:
        raise ValueError("按钮文本不能为空")
    if 点击类型 not in {"", "link", "return-val"}:
        raise ValueError("点击类型只能为 link 或 return-val")
    if 文本类型 not in {"plain-text", "kmarkdown"}:
        raise ValueError("按钮文本类型只能为 plain-text 或 kmarkdown")
    if 回调 is not None:
        if not 值:
            raise ValueError("绑定回调的按钮必须提供非空的 值 字段")
        if 点击类型 == "link":
            raise ValueError("link 按钮跳转链接，不能绑定回调；请去掉 回调 参数")
        if 点击类型 == "":
            点击类型 = "return-val"  # 有回调时默认回传 value，保证点击事件可触发
        # 登记回调(以 value 为键，覆盖式)，点击事件到达后由机器人取出调用
        按钮回调中心.注册(值, 回调)
    # 文本内容字典，作为按钮的子元素 text
    文本元素: dict[str, Any] = {"type": 文本类型, "content": 文本}
    return {"type": "button", "theme": 主题, "value": 值, "click": 点击类型, "text": 文本元素}


class 卡片:
    """KOOK 单张卡片，负责累积各类模块并导出可供发送的字典；所有添加方法均支持链式调用。"""

    def __init__(self, 颜色: str = "#007AFF", 主题: str = "primary", 尺寸: str = "lg"):
        """
        初始化一张空卡片。
        参数:
            颜色: 卡片边框十六进制色值(如 "#007AFF")；填写后边框优先按颜色渲染。
            主题: 卡片主题，取值见卡片主题集合，默认 primary。
            尺寸: 卡片大小，只能取 sm 或 lg，默认 lg。
        异常:
            ValueError: 主题或尺寸取值不在合法集合内。
        """
        if 主题 not in 卡片主题集合:
            raise ValueError(f"主题只能为 {'、'.join(卡片主题集合)}")
        if 尺寸 not in 卡片尺寸集合:
            raise ValueError(f"卡片尺寸只能为 sm 或 lg")
        # 默认卡片字典：type 恒为 card，modules 累积该卡片上的全部模块
        self.默认卡片: dict[str, Any] = {
            "type": "card",
            "theme": 主题,
            "color": 颜色,
            "size": 尺寸,
            "modules": [],
        }

    def 修改卡片(self, 颜色: str | None = None, 主题: str | None = None, 尺寸: str | None = None) -> "卡片":
        """
        修改卡片的外观配置，传 None 的参数保持不变。
        参数:
            颜色: 新的边框十六进制色值。
            主题: 新的主题，取值见卡片主题集合。
            尺寸: 新的尺寸，只能取 sm 或 lg。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 传入的主题或尺寸不合法。
        """
        if 颜色 is not None:
            self.默认卡片["color"] = 颜色
        if 主题 is not None:
            if 主题 not in 卡片主题集合:
                raise ValueError(f"主题只能为 {'、'.join(卡片主题集合)}")
            self.默认卡片["theme"] = 主题
        if 尺寸 is not None:
            if 尺寸 not in 卡片尺寸集合:
                raise ValueError("卡片尺寸只能为 sm 或 lg")
            self.默认卡片["size"] = 尺寸
        return self

    def 添加模块(self, 模块: dict[str, Any]) -> "卡片":
        """
        通用入口：把任意合法模块字典追加到卡片 modules 列表。
        参数:
            模块: 符合 KOOK 模块结构的字典。
        返回:
            当前卡片对象，便于链式继续添加模块。
        """
        self.默认卡片["modules"].append(模块)
        return self

    def 添加标题模块(self, 标题: str) -> "卡片":
        """
        添加 header 标题模块，展示突出的大字号标题。
        参数:
            标题: 标题文本，纯文本，最大 100 个字符。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 标题为空或超过 100 个字符。
        """
        if not 标题 or len(标题) > 100:
            raise ValueError("标题不能为空或长度超过 100 个字符")
        return self.添加模块({
            "type": "header",
            "text": {
                "type": "plain-text",
                "content": 标题,
            }
        })

    def 添加内容模块(self, 内容: str, 内容类型: str = "plain-text",
                    附件: dict[str, Any] | None = None, 附件位置: str = "right") -> "卡片":
        """
        添加 section 内容模块，展示一段文本并可选择在左侧/右侧附带图片或按钮。
        参数:
            内容: 正文文本。
            内容类型: 文本格式，取 plain-text(≤2000字) 或 kmarkdown(≤5000字)。
            附件: 可选元素字典，只能为图片或按钮元素。
            附件位置: 附件所在侧，left 或 right；按钮不允许放在左侧。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 参数内容类型、附件类型或附件位置不合法。
        """
        if 内容类型 not in {"plain-text", "kmarkdown"}:
            raise ValueError("内容类型只能为 plain-text 或 kmarkdown")
        if 附件位置 not in {"left", "right"}:
            raise ValueError("附件位置只能为 left 或 right")
        if 附件 is not None:
            if 附件.get("type") not in {"image", "button"}:
                raise ValueError("附件只能为图片或按钮元素")
            if 附件.get("type") == "button" and 附件位置 == "left":
                raise ValueError("按钮不能放置在 section 的左侧")
        # 内容模块字典：text 为文本元素，mode 声明附件方位，accessory 仅在存在附件时写入
        内容模块: dict[str, Any] = {
            "type": "section",
            "mode": 附件位置,
            "text": {"type": 内容类型, "content": 内容},
        }
        if 附件 is not None:
            内容模块["accessory"] = 附件
        return self.添加模块(内容模块)

    def 添加段落模块(self, 字段内容列表: list[str], 列数: int = 3, 内容类型: str = "kmarkdown") -> "卡片":
        """
        添加含 paragraph 分栏结构的 section 模块，把多个文本自动排成左右分栏。
        参数:
            字段内容列表: 各栏文本内容列表，每项是一段文本。
            列数: 分栏列数，可取值 1-3，移动端忽略。
            内容类型: 栏内文本格式，取 plain-text 或 kmarkdown。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 列数、内容类型或字段数量不合法。
        """
        if 列数 not in {1, 2, 3}:
            raise ValueError("列数只能为 1、2 或 3")
        if 内容类型 not in {"plain-text", "kmarkdown"}:
            raise ValueError("内容类型只能为 plain-text 或 kmarkdown")
        if not 字段内容列表 or len(字段内容列表) > 50:
            raise ValueError("字段内容数量需在 1-50 之间")
        # 逐个把字符串包装成文本元素，fields 只接受文本类元素
        字段元素列表: list[dict[str, Any]] = [{"type": 内容类型, "content": 内容} for 内容 in 字段内容列表]
        return self.添加模块({
            "type": "section",
            "text": {
                "type": "paragraph",
                "cols": 列数,
                "fields": 字段元素列表,
            }
        })

    def 添加图片组模块(self, 图片地址列表: list[str], 替代文字: str = "") -> "卡片":
        """
        添加 image-group 图片组模块，1-9 张图片以正方缩略图网格展示。
        参数:
            图片地址列表: 图片 URL 列表，数量需在 1-9 之间。
            替代文字: 每张图片统一的替代文字。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 图片数量不在 1-9 范围内。
        """
        if not 图片地址列表 or len(图片地址列表) > 9:
            raise ValueError("图片数量需在 1-9 之间")
        # 把地址批量包装为图片元素字典，elements 中只允许 image 元素
        图片元素列表: list[dict[str, Any]] = [创建图片元素(地址, 替代文字) for 地址 in 图片地址列表]
        return self.添加模块({"type": "image-group", "elements": 图片元素列表})

    def 添加图片容器模块(self, 图片地址列表: list[str], 替代文字: str = "") -> "卡片":
        """
        添加 container 容器模块，1-9 张图片按原比例纵向排列展示。
        参数:
            图片地址列表: 图片 URL 列表，数量需在 1-9 之间。
            替代文字: 每张图片统一的替代文字。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 图片数量不在 1-9 范围内。
        """
        if not 图片地址列表 or len(图片地址列表) > 9:
            raise ValueError("图片数量需在 1-9 之间")
        # 与图片组结构相同，区别在于图片不裁剪为正方形，而是纵向排列
        图片元素列表: list[dict[str, Any]] = [创建图片元素(地址, 替代文字) for 地址 in 图片地址列表]
        return self.添加模块({"type": "container", "elements": 图片元素列表})

    def 添加交互模块(self, 按钮元素列表: list[dict[str, Any]]) -> "卡片":
        """
        添加 action-group 交互模块，把按钮元素排成一行。
        参数:
            按钮元素列表: 由创建按钮元素生成的按钮字典列表，最多 4 个。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 按钮数量不在 1-4 范围内或列表内存在非按钮元素。
        """
        if not 按钮元素列表 or len(按钮元素列表) > 4:
            raise ValueError("按钮数量需在 1-4 之间")
        for 按钮元素 in 按钮元素列表:
            if 按钮元素.get("type") != "button":
                raise ValueError("交互模块中只能包含 button 元素")
        return self.添加模块({"type": "action-group", "elements": 按钮元素列表})

    def 添加备注模块(self, 元素列表: list[dict[str, Any]]) -> "卡片":
        """
        添加 context 备注模块，展示一行图文混排的小字备注。
        参数:
            元素列表: 文本或图片元素字典列表，最多 10 个元素。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 元素数量不在 1-10 范围内或存在不支持的子元素类型。
        """
        if not 元素列表 or len(元素列表) > 10:
            raise ValueError("备注元素数量需在 1-10 之间")
        # context 仅允许 plain-text、kmarkdown、image 三种元素
        支持类型集合: frozenset[str] = frozenset({"plain-text", "kmarkdown", "image"})
        for 元素 in 元素列表:
            if 元素.get("type") not in 支持类型集合:
                raise ValueError("备注模块中只能包含文本或图片元素")
        return self.添加模块({"type": "context", "elements": 元素列表})

    def 添加分割线模块(self) -> "卡片":
        """
        添加 divider 分割线模块，作为卡片内视觉分隔。
        返回:
            当前卡片对象，便于链式继续添加模块。
        """
        return self.添加模块({"type": "divider"})

    def 添加文件模块(self, 来源地址: str, 标题: str = "", 模块类型: str = "file", 封面地址: str = "") -> "卡片":
        """
        添加 file/audio/video 媒体模块，展示可下载或播放的文件。
        参数:
            来源地址: 文件、音频或视频的资源 URL。
            标题: 媒体显示的标题。
            模块类型: 媒体类型，只能取 file、audio 或 video。
            封面地址: 封面图 URL，仅 audio 类型生效。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 来源地址为空或模块类型不合法。
        """
        if not 来源地址:
            raise ValueError("来源地址不能为空")
        if 模块类型 not in {"file", "audio", "video"}:
            raise ValueError("模块类型只能为 file、audio 或 video")
        # 媒体模块基础字典，封面仅在填写时写入(只对音频有意义)
        媒体模块: dict[str, Any] = {"type": 模块类型, "src": 来源地址, "title": 标题}
        if 封面地址 and 模块类型 == "audio":
            媒体模块["cover"] = 封面地址
        return self.添加模块(媒体模块)

    def 添加倒计时模块(self, 结束时间戳: int, 模式: str = "day", 开始时间戳: int | None = None) -> "卡片":
        """
        添加 countdown 倒计时模块。
        参数:
            结束时间戳: 到期时间的毫秒时间戳，不能早于服务器当前时间。
            模式: 倒计时展示样式，day 按天、hour 按小时、second 按秒。
            开始时间戳: 起始毫秒时间戳，仅 second 模式才有该字段，可选。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 模式不合法或时间戳非法。
        """
        if 模式 not in {"day", "hour", "second"}:
            raise ValueError("倒计时模式只能为 day、hour 或 second")
        if 结束时间戳 <= 0 or (开始时间戳 is not None and 开始时间戳 <= 0):
            raise ValueError("时间戳必须为正整数(毫秒)")
        # 倒计时模块字典，startTime 仅 second 模式时写入
        倒计时模块: dict[str, Any] = {"type": "countdown", "endTime": 结束时间戳, "mode": 模式}
        if 模式 == "second" and 开始时间戳 is not None:
            倒计时模块["startTime"] = 开始时间戳
        return self.添加模块(倒计时模块)

    def 添加邀请模块(self, 邀请码: str) -> "卡片":
        """
        添加 invite 邀请模块，展示服务器/语音频道邀请入口。
        参数:
            邀请码: 邀请链接或邀请码。
        返回:
            当前卡片对象，便于链式继续添加模块。
        异常:
            ValueError: 邀请码为空。
        """
        if not 邀请码:
            raise ValueError("邀请码不能为空")
        return self.添加模块({"type": "invite", "code": 邀请码})

    def 导出(self) -> dict[str, Any]:
        """
        导出当前卡片的完整 JSON 字典。
        返回:
            可直接放入卡片消息数组中的卡片字典。
        """
        return self.默认卡片


def 构建卡片消息(卡片列表: list[卡片]) -> list[dict[str, Any]]:
    """
    把 1-5 张卡片组装成一条可发送的卡片消息(JSON 数组)。
    参数:
        卡片列表: 卡片对象列表，最多 5 张，全部模块总数不超过 50。
    返回:
        卡片消息数组，其元素为各卡片的导出字典。
    异常:
        ValueError: 卡片数量超过 5 或模块总数超过 50。
    """
    if not 卡片列表 or len(卡片列表) > 5:
        raise ValueError("一条卡片消息需包含 1-5 张卡片")
    # 统计所有卡片的模块数量，服务端限制整条消息最多 50 个模块
    模块总数: int = sum(len(卡片.默认卡片["modules"]) for 卡片 in 卡片列表)
    if 模块总数 > 50:
        raise ValueError("一条卡片消息的模块总数不能超过 50")
    # 消息本体即各卡片字典组成的数组
    return [卡片.导出() for 卡片 in 卡片列表]


def 序列化卡片消息(卡片列表: list[卡片]) -> str:
    """
    把卡片消息序列化为 JSON 字符串，即消息接口 content 字段要填写的值。
    参数:
        卡片列表: 卡片对象列表，规则同构建卡片消息。
    返回:
        可直接发送的卡片消息 JSON 字符串(消息类型为 10)。
    异常:
        ValueError: 卡片数量或模块数量超限。
    """
    消息数组: list[dict[str, Any]] = 构建卡片消息(卡片列表)
    # 调用库函数：把 Python 对象转成 JSON 字符串
    # 传入：obj=消息数组(卡片消息列表)，ensure_ascii=False(保留中文原样输出)
    # 作用：将卡片字典列表序列化为符合 KOOK 发送接口要求的 JSON 文本
    # 传出：str 类型的 JSON 字符串
    return json.dumps(消息数组, ensure_ascii=False)
