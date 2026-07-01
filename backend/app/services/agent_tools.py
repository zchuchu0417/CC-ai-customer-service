"""Agent 工具集合 - AI 可调用的"动手"能力

每个工具：
1. mock 数据 + 真实逻辑（生产时换成调 OA / 订单系统 / 工单系统）
2. OpenAI 标准 tool schema（让 LLM 知道怎么调）
3. 函数签名 = JSON Schema 中描述的参数

PM 视角：
- 工具是 AI 产品的"手"，没有工具的 AI 只能"说"
- 工具粒度：单一职责，便于 LLM 决策
- 入参出参 JSON Schema 描述，字段必带 description（给 LLM 看）
"""
import random
import uuid
from datetime import datetime, timedelta


# ============================================================
# Mock 数据（生产时替换为调外部 API）
# ============================================================

MOCK_ORDERS = {
    "ORD20250603": {
        "order_id": "ORD20250603",
        "user_name": "测试用户 1",
        "items": [
            {"sku": "SKU-CC-2026-SHOE-001", "name": "CC Run X1 男女款运动跑鞋", "color": "经典黑", "size": "42", "price": 299, "qty": 1}
        ],
        "total_amount": 299,
        "status": "shipped",
        "created_at": "2026-06-21 14:30",
        "shipped_at": "2026-06-22 09:15",
        "logistics": {
            "carrier": "顺丰速运",
            "tracking_no": "SF1234567890",
            "current_location": "上海浦东中转站",
            "expected_delivery": "2026-06-25 18:00",
            "last_update": "2026-06-24 08:30",
        },
    },
    "ORD20250601": {
        "order_id": "ORD20250601",
        "user_name": "测试用户 1",
        "items": [
            {"sku": "SKU-CC-2026-AUDIO-001", "name": "CC Pods Pro 无线蓝牙耳机", "color": "星空黑", "price": 499, "qty": 1}
        ],
        "total_amount": 499,
        "status": "delivered",
        "created_at": "2026-06-15 10:00",
        "delivered_at": "2026-06-17 14:20",
    },
    "ORD20250520": {
        "order_id": "ORD20250520",
        "user_name": "测试用户 1",
        "items": [
            {"sku": "SKU-CC-2026-SHOE-001", "name": "CC Run X1 男女款运动跑鞋", "color": "海洋蓝", "size": "39", "price": 299, "qty": 1}
        ],
        "total_amount": 299,
        "status": "refunded",
        "created_at": "2026-05-20 16:45",
        "refunded_at": "2026-05-25 10:30",
    },
}


# ============================================================
# 工具实现
# ============================================================

def query_order(order_id: str) -> dict:
    """查询订单详情"""
    order = MOCK_ORDERS.get(order_id.upper().strip())
    if not order:
        return {
            "success": False,
            "error": f"未找到订单 {order_id}",
            "suggestion": "请确认订单号是否正确。订单号格式：ORDxxxxxxxx",
        }
    return {"success": True, "order": order}


def create_return_request(order_id: str, reason: str) -> dict:
    """为已购订单创建退货申请"""
    order = MOCK_ORDERS.get(order_id.upper().strip())
    if not order:
        return {
            "success": False,
            "error": f"未找到订单 {order_id}",
        }

    if order["status"] == "refunded":
        return {
            "success": False,
            "error": f"订单 {order_id} 已退款，无需重复申请",
        }

    if order["status"] not in ("paid", "shipped", "delivered"):
        return {
            "success": False,
            "error": f"订单当前状态为 {order['status']}，不支持退货",
        }

    # 生成 mock 退货单
    return_id = f"RET{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"

    return {
        "success": True,
        "return_id": return_id,
        "order_id": order_id,
        "refund_amount": order["total_amount"],
        "reason": reason,
        "status": "pending_review",
        "estimated_days": "1-3 个工作日",
        "next_step": "请等待短信通知，审核通过后会有快递上门取件",
    }


def escalate_to_human(reason: str, urgency: str = "normal") -> dict:
    """转接人工客服"""
    if urgency not in ("low", "normal", "high"):
        urgency = "normal"

    # mock 排队信息
    queue_info = {
        "low": (8, "10-15 分钟"),
        "normal": (3, "3-5 分钟"),
        "high": (1, "1-2 分钟"),
    }
    queue_position, wait_time = queue_info[urgency]

    ticket_id = f"TKT{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return {
        "success": True,
        "ticket_id": ticket_id,
        "reason": reason,
        "urgency": urgency,
        "queue_position": queue_position,
        "estimated_wait": wait_time,
        "channel": "已为您接入在线人工客服，请保持页面打开",
        # 🆕 显式给 AI 范文（防它编电话号码）
        "ai_response_template": (
            f"已为您紧急转接人工客服，工单号 {ticket_id}，"
            f"当前排队第 {queue_position} 位，预计 {wait_time} 内有客服联系您。"
            "请保持本页面打开。"
            "（请勿在回答中编造具体客服电话号码，CC 商城具体联系方式请查看官网底部。）"
        ),
    }


# ============================================================
# 工具注册表 + OpenAI Schema
# ============================================================

TOOL_REGISTRY = {
    "query_order": query_order,
    "create_return_request": create_return_request,
    "escalate_to_human": escalate_to_human,
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "查询订单的详细信息，包括订单状态、商品明细、金额、物流轨迹、收货时间等。当用户提到具体订单号、询问'我的订单到哪了'、'什么时候发货'等问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单号，格式如 ORD20250603（区分大小写，会自动转大写）",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_return_request",
            "description": "为指定订单创建退货申请。当用户明确表达想退货、退款、不想要了等意图，且提供了订单号时调用。务必先调 query_order 确认订单存在并符合退货条件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "要退货的订单号",
                    },
                    "reason": {
                        "type": "string",
                        "description": "退货原因，比如：质量问题、不喜欢、尺码不合适、不再需要等",
                    },
                },
                "required": ["order_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "转接人工客服。当遇到以下情况时调用：① 用户明确要求'转人工'、'找客服'、'真人' ② AI 无法回答的复杂问题 ③ 用户情绪激烈（愤怒、辱骂、严重投诉）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "转人工的原因简述",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "紧急程度：high=情绪激烈/严重投诉, normal=一般问题, low=不紧急",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict) -> dict:
    """统一工具执行入口（含异常捕获）"""
    func = TOOL_REGISTRY.get(name)
    if not func:
        return {"success": False, "error": f"未知工具 {name}"}
    try:
        return func(**arguments)
    except TypeError as e:
        return {"success": False, "error": f"参数错误: {e}"}
    except Exception as e:
        return {"success": False, "error": f"工具执行失败: {str(e)[:100]}"}
