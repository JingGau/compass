from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class IntakeResult:
    ok: bool
    raw_problem: str
    standard_problem: str
    scene: str
    environment: str
    entities: dict[str, str | None]
    missing: list[dict[str, str | bool]]
    investigation_hints: list[dict[str, str]]
    next_actions: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


SCENE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("payment", ("支付", "收单", "支付宝", "微信", "预付款", "退款", "入金", "礼品卡", "余额付")),
    ("settlement", ("结算", "清分", "分账", "提现", "钱包", "商户")),
    ("order", ("订单", "计费", "价格", "结算价")),
    ("charging", ("充电", "桩", "枪", "停充", "实时单")),
    ("b_side", ("后台", "B端", "运营商", "页面", "菜单")),
)


def intake_problem(text: str) -> IntakeResult:
    problem = " ".join(text.strip().split())
    scene = _classify_scene(problem)
    entities = _extract_entities(problem)
    missing = _missing_entities(scene, entities, problem)
    investigation_hints = _investigation_hints(scene)
    return IntakeResult(
        ok=True,
        raw_problem=problem,
        standard_problem=_standard_problem(problem, scene),
        scene=scene,
        environment=_extract_environment(problem),
        entities=entities,
        missing=missing,
        investigation_hints=investigation_hints,
        next_actions=_next_actions(missing),
    )


def _classify_scene(text: str) -> str:
    for scene, keywords in SCENE_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return scene
    return "unknown"


def _extract_entities(text: str) -> dict[str, str | None]:
    return {
        "order_no": _first_match(text, (r"订单号[:：\s]*([A-Za-z0-9_-]{4,})", r"\border[_-]?no[:：=\s]*([A-Za-z0-9_-]{4,})")),
        "pay_no": _first_match(text, (r"支付单号[:：\s]*([A-Za-z0-9_-]{4,})", r"\bpay[_-]?no[:：=\s]*([A-Za-z0-9_-]{4,})")),
        "user_id": _first_match(text, (r"user[_-]?id[:：=\s]*([A-Za-z0-9_-]{3,})", r"用户ID[:：\s]*([A-Za-z0-9_-]{3,})")),
        "phone": _first_match(text, (r"(?<!\d)(1[3-9]\d{9})(?!\d)",)),
        "time_range": _extract_time_range(text),
    }


def _extract_environment(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in ("uat", "预发")):
        return "uat"
    if any(marker in lowered for marker in ("test", "测试环境", "测试库")):
        return "test"
    if any(marker in lowered for marker in ("prod", "生产", "线上")):
        return "prod"
    return "prod"


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_time_range(text: str) -> str | None:
    time_words = (
        "今天",
        "昨天",
        "上午",
        "下午",
        "晚上",
        "最近",
        "刚刚",
        "一小时",
        "半小时",
        "当天",
    )
    if any(word in text for word in time_words):
        return "用户描述中的相对时间"
    match = re.search(r"\d{4}-\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{2})?", text)
    if match:
        return match.group(0)
    return None


def _missing_entities(scene: str, entities: dict[str, str | None], text: str) -> list[dict[str, str | bool]]:
    missing: list[dict[str, str | bool]] = []
    has_object = bool(entities.get("order_no") or entities.get("pay_no") or entities.get("user_id") or entities.get("phone"))
    if scene in {"payment", "settlement", "order", "charging"} and not has_object:
        missing.append(
            {
                "name": "定位对象",
                "blocking": True,
                "alternative": "订单号 / 支付单号 / 用户ID / 手机号",
                "question": "请补充一个能定位交易的对象。",
            }
        )
    if not entities.get("time_range"):
        missing.append(
            {
                "name": "时间范围",
                "blocking": not bool("最近一天" in text or "当天" in text),
                "alternative": "最近30分钟 / 1小时 / 当天",
                "question": "请补充问题发生的大概时间范围。",
            }
        )
    return missing


def _standard_problem(text: str, scene: str) -> str:
    prefix = {
        "payment": "支付/收单问题",
        "settlement": "结算/清分问题",
        "order": "订单/计费问题",
        "charging": "充电链路问题",
        "b_side": "B端后台问题",
    }.get(scene, "待分类问题")
    return f"{prefix}：{text}"


def _investigation_hints(scene: str) -> list[dict[str, str]]:
    presets = {
        "payment": ["支付回调未到达或处理失败", "支付成功但业务单状态推进失败", "收单渠道与内部支付单映射异常"],
        "settlement": ["清分单生成时机或状态判断异常", "入金通知只作为推送银行的允许信号", "退款垫资与清分状态存在先后顺序差异"],
        "order": ["订单状态机推进失败", "计费/结算价计算结果阻断后续流程", "支付单与订单关联缺失"],
        "charging": ["实时单状态未推进", "桩枪绑定或停充回调异常", "充电明细数据未完整上报"],
        "b_side": ["页面操作对象或权限上下文不完整", "后端接口参数与页面状态不一致", "数据权限过滤导致结果异常"],
        "unknown": ["输入信息不足，需要先补充定位实体"],
    }
    return [
        {
            "id": f"D{i + 1}",
            "type": "candidate_direction",
            "statement": item,
            "status": "reference_only",
        }
        for i, item in enumerate(presets.get(scene, presets["unknown"])[:3])
    ]


def _next_actions(missing: list[dict[str, str | bool]]) -> list[str]:
    blocking = [item for item in missing if item.get("blocking")]
    if blocking:
        return [str(blocking[0]["question"])]
    return ["生成查询计划，并优先查询最能验证 H1 的证据源。"]
