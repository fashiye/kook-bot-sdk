# -*- coding: utf-8 -*-
'''
KOOK 库 API 参考自动生成脚本(临时工具)。
遍历 kook库 各模块，把类/函数/方法签名与 docstring 提取为 Markdown，
写入 文档/API参考/ 目录，保证与源码同步的"全量"接口清单。
'''
import importlib        # 按名称动态导入模块
import inspect          # 反射获取签名与源码信息
import re               # 正则压缩长类型路径
import sys              # 修改模块搜索路径
from pathlib import Path        # 构造与检查路径

# 动态定位：文件位于 kook库/文档/tools/ 下
当前目录: Path = Path(__file__).resolve()
包根目录: Path = 当前目录.parents[2]          # kook库 包根
导入根目录: Path = 当前目录.parents[3]        # 含 kook库 包的上层目录
sys.path.insert(0, str(导入根目录))

# 输出目录：kook库/文档/API参考
输出根: Path = 包根目录 / "文档" / "API参考"

# 分组: (目标文件名, [(模块路径, 显示标题), ...])
分组 = [
    ("01_模型层.md", [
        ("模型.类型", "类型定义(枚举)"),
        ("模型.错误", "异常类型"),
        ("模型.事件", "事件对象"),
        ("模型.对象", "类型化数据对象"),
        ("模型.常量", "接口常量"),
    ]),
    ("02_模型_卡片.md", [
        ("模型.卡片", "卡片消息基础"),
        ("模型.卡片模板", "卡片模板库"),
    ]),
    ("10_核心层.md", [
        ("核心.HTTP引擎", "REST 请求引擎"),
        ("核心.资源基座", "资源基类与工具"),
        ("核心.网关", "WebSocket 网关"),
    ]),
    ("20_资源_客户端与机器人.md", [
        ("资源.客户端", "Bot 聚合客户端"),
        ("资源.机器人", "机器人主类(含语法糖)"),
    ]),
    ("30_资源_消息.md", [
        ("资源.消息.频道消息", "频道消息资源"),
        ("资源.消息.私信", "私信消息与会话资源"),
    ]),
    ("31_资源_服务器.md", [
        ("资源.服务器.服务器", "服务器资源(含静音/助力)"),
        ("资源.服务器.角色", "服务器角色资源"),
        ("资源.服务器.表情", "服务器表情资源"),
        ("资源.服务器.邀请", "邀请资源"),
    ]),
    ("32_资源_频道.md", [
        ("资源.频道.频道", "频道资源"),
        ("资源.频道.频道角色权限", "频道角色权限资源"),
        ("资源.频道.语音", "语音资源"),
    ]),
    ("33_资源_其他.md", [
        ("资源.用户", "用户资源"),
        ("资源.素材", "素材上传资源"),
        ("资源.帖子", "帖子资源"),
        ("资源.模板", "消息模板资源"),
    ]),
]


def 压缩类型文本(文本: str) -> str:
    """
    把 docstring/签名中形如 kook库.资源.xxx.类 的完整路径压缩为末段类名。
    参数:
        文本: 原始文本。
    返回:
        压缩后的文本。
    """
    # 正则：匹配以 kook库. 开头、由点分隔的多段路径，保留最后一段
    return re.sub(r"kook库(?:\.[^\s,()\[\]{}]+)+",
                  lambda m: m.group(0).rsplit(".", 1)[-1], 文本)


def 首行摘要(文本: str, 上限: int = 160) -> str:
    """
    取文本第一个非空行作为摘要。
    参数:
        文本: 待提取文本。
        上限: 摘要长度上限。
    返回:
        摘要文本。
    """
    for 行 in 文本.splitlines():
        干净行: str = 行.strip()
        if 干净行:
            return 干净行 if len(干净行) <= 上限 else 干净行[:上限] + "…"
    return ""


def 剩余说明(文本: str) -> str:
    """
    取文本去掉首行后的剩余正文(参数/返回/异常说明)。
    参数:
        文本: docstring 原文。
    返回:
        剩余正文(保留换行)。
    """
    全部行 = 文本.splitlines()
    if not 全部行:
        return ""
    return "\n".join(全部行[1:]).strip()


def 模块摘要(模块) -> str:
    """
    取模块 docstring 的首行作为模块简介。
    参数:
        模块: 已导入的模块对象。
    返回:
        摘要文本。
    """
    if not 模块.__doc__:
        return ""
    return 压缩类型文本(首行摘要(模块.__doc__, 200))


def 类与函数列表(模块, 类型) -> list[object]:
    """
    列出某模块中"自己定义"的成员(类或函数，排除导入项)。
    参数:
        模块: 模块对象。
        类型: 过滤类型(类或函数)。
    返回:
        成员对象列表。
    """
    结果: list[object] = []
    for 名称 in dir(模块):
        if 名称.startswith("_"):
            continue
        成员 = getattr(模块, 名称)
        if not isinstance(成员, 类型):
            continue
        # 只保留本源文件定义的成员(排除 from … import 进来的)
        if getattr(成员, "__module__", None) != 模块.__name__:
            continue
        # 跳过 dataclass 的默认字段对象等
        if 类型 is type and inspect.isdatadescriptor(成员):
            continue
        结果.append(成员)
    # 按源码行号排序，保持书写顺序
    return sorted(结果, key=lambda 成员: inspect.getsourcelines(成员)[1])


def 签名文本(成员) -> str:
    """
    格式化函数/方法签名并压缩类型路径。
    参数:
        成员: 函数或方法对象。
    返回:
        便于阅读的签名文本。
    """
    try:
        原始 = str(inspect.signature(成员))
    except (ValueError, TypeError):
        原始 = "(签名不可用)"
    return 压缩类型文本("def " + 成员.__name__ + 原始)


def 渲染成员(成员, 是否方法: bool) -> list[str]:
    """
    把一个函数/方法渲染成 Markdown 片段。
    参数:
        成员: 函数或方法对象。
        是否方法: 是否为类方法(标题层级不同)。
    返回:
        Markdown 行列表。
    """
    行: list[str] = []
    摘要: str = ""
    全文: str = ""
    if 成员.__doc__:
        全文 = 压缩类型文本(成员.__doc__).strip()
        摘要 = 首行摘要(全文)
    if 是否方法:
        行.append(f"- **{成员.__name__}** — {摘要}")
        行.append("")
        行.append("  ```python")
        行.append("  " + 签名文本(成员))
        行.append("  ```")
    else:
        行.append(f"### `{成员.__name__}`")
        行.append("")
        行.append(f"{摘要}")
        行.append("")
        行.append("```python")
        行.append(签名文本(成员))
        行.append("```")
    if 成员.__doc__:
        # 把去掉首行后的完整 docstring(参数/返回/异常说明)以引用块保留，形成全量说明
        详情 = 剩余说明(全文)
        if 详情:
            行.append("")
            行.append("<details><summary>参数 / 返回 / 异常 完整说明</summary>")
            行.append("")
            for 行段 in 详情.splitlines():
                干净段: str = 行段.strip()
                行.append(f"> {干净段}" if 干净段 else ">")
            行.append("")
            行.append("</details>")
    行.append("")
    return 行


def 渲染类(类) -> list[str]:
    """
    把一个类(含枚举/dataclass/普通类)渲染为 Markdown 片段。
    参数:
        类: 类对象。
    返回:
        Markdown 行列表。
    """
    行: list[str] = []
    标题: str = 类.__name__
    行.append(f"## `{标题}`")
    行.append("")
    if 类.__doc__:
        摘要 = 压缩类型文本(类.__doc__).strip().split("\n\n")[0].replace("\n", " ")
        行.append(f"{摘要}")
        行.append("")
    try:
        文件 = inspect.getsourcefile(类)
        行号 = inspect.getsourcelines(类)[1]
        行.append(f"> 源码位置：`{文件.split('kook库')[-1]}` 第 {行号} 行")
        行.append("")
    except (OSError, TypeError):
        pass

    # 枚举成员表
    try:
        from enum import Enum
        if issubclass(类, Enum):
            行.append("| 成员 | 值 |")
            行.append("|---|---|")
            for 名 in 类.__members__:
                行.append(f"| {名} | `{类.__members__[名].value}` |")
            行.append("")
            return 行
    except TypeError:
        pass

    # dataclass 字段
    if hasattr(类, "__dataclass_fields__"):
        行.append("**字段**：" + "、".join(类.__dataclass_fields__.keys()))
        行.append("")

    # 方法(含以单下划线开头的重要内部方法，如资源基座的 _请求)
    方法列表: list = []
    for 名, 方法 in inspect.getmembers(类, predicate=inspect.isfunction):
        if 名.startswith("__"):
            continue
        if getattr(方法, "__qualname__", "").split(".")[0] != 类.__name__:
            continue
        方法列表.append(方法)
    方法列表.sort(key=lambda m: inspect.getsourcelines(m)[1])
    for 方法 in 方法列表:
        行.extend(渲染成员(方法, True))
    return 行


def 生成单模块(模块, 标题: str) -> list[str]:
    """
    生成某模块的完整 Markdown 章节。
    参数:
        模块: 模块对象。
        标题: 模块展示标题。
    返回:
        Markdown 行列表。
    """
    行: list[str] = []
    行.append(f"## `{模块.__name__}` —— {标题}")
    行.append("")
    行.append(模块摘要(模块))
    行.append("")
    # 模块级函数
    for 函数 in 类与函数列表(模块, __import__("types").FunctionType):
        行.extend(渲染成员(函数, False))
    # 类
    for 类 in 类与函数列表(模块, type):
        行.extend(渲染类(类))
    return 行


def 主流程() -> None:
    """遍历分组并写出各 Markdown 文件。返回: 无返回值。"""
    输出根.mkdir(parents=True, exist_ok=True)
    索引: list[str] = []
    for 文件名, 模块清单 in 分组:
        全行: list[str] = [f"# {文件名.replace('.md','').split('_',1)[1] if '_' in 文件名 else 文件名}", "",]
        for 模块路径, 标题 in 模块清单:
            模块 = importlib.import_module("kook库." + 模块路径)
            全行.extend(生成单模块(模块, 标题))
        输出 = "\n".join(行 for 行 in 全行 if 行 is not None)
        (输出根 / 文件名).write_text(输出, encoding="utf-8")
        索引.append(f"- [{文件名}](API参考/{文件名}) 约 {len(输出)//1000} KB")
        print(f"[生成] {文件名}: {len(输出)} 字符")
    print("全量 API 参考生成完成")


if __name__ == "__main__":
    主流程()
