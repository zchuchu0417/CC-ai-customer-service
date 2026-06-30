"""情绪检测服务 - 关键词 + 强度评分（v1 MVP）

设计权衡（PM 视角）：
- v1 用关键词词库 + 简单评分：零成本、毫秒级、覆盖 80% 真实场景
- v2 可升级为 LLM 调用判断：精度更高但慢 1s + 增加成本
- v3 可训练专用情感分类模型：精度天花板但运维复杂

当前选 v1：MVP 阶段够用，所有真实情绪都靠"关键词信号 + 标点强度"即可。
"""
from typing import Literal

# ============================================================
# 情绪词库（分等级）
# ============================================================
EMOTION_KEYWORDS = {
    "anger": {  # 愤怒
        "high": [
            "气死了", "气死我了", "tmd", "尼玛", "妈的", "fuck", "shit",
            "滚", "废物", "垃圾", "智障", "脑残", "操",
        ],
        "medium": [
            "生气", "气人", "火大", "愤怒", "无语", "弱智", "蠢",
            "搞什么", "什么破", "什么烂",
        ],
        "low": ["烦", "心烦", "不爽", "讨厌", "郁闷"],
    },
    "disappointment": {  # 失望
        "high": ["太差了", "极差", "失望透顶", "彻底失望", "毁了", "完蛋了"],
        "medium": ["失望", "差劲", "破", "坏", "次品", "假货"],
        "low": ["一般", "不行", "不好用", "不咋样"],
    },
    "anxiety": {  # 焦虑
        "high": ["急死了", "急啊", "急死人", "完了", "怎么办啊"],
        "medium": ["急", "焦虑", "担心", "怎么办", "求", "拜托"],
        "low": ["不确定", "希望", "麻烦"],
    },
    "complaint": {  # 投诉倾向
        "high": ["投诉", "起诉", "曝光", "315", "消协", "工商局", "黑猫"],
        "medium": ["不满", "抗议", "举报"],
        "low": ["反映", "建议", "意见"],
    },
}

# 强度评分映射
INTENSITY_MAP = {"high": 8, "medium": 5, "low": 3}

# 情绪标签中文名
EMOTION_CN = {
    "anger": "愤怒",
    "disappointment": "失望",
    "anxiety": "焦虑",
    "complaint": "投诉倾向",
    "neutral": "中性",
}

EmotionLabel = Literal["anger", "disappointment", "anxiety", "complaint", "neutral"]


def detect_emotion(content: str) -> dict:
    """检测一段文本的情绪

    Returns:
        {
            "label": "anger" / "disappointment" / "anxiety" / "complaint" / "neutral",
            "intensity": 0-10,
            "matched_keywords": ["气死了", ...],
            "label_cn": "愤怒",
        }
    """
    if not content:
        return {"label": "neutral", "intensity": 0, "matched_keywords": [], "label_cn": "中性"}

    text = content.lower()

    best_emotion = "neutral"
    best_intensity = 0
    matched = []

    # 遍历所有情绪类型 + 等级
    for emotion, levels in EMOTION_KEYWORDS.items():
        for level, keywords in levels.items():
            for kw in keywords:
                if kw in text:
                    matched.append(kw)
                    score = INTENSITY_MAP[level]
                    if score > best_intensity:
                        best_emotion = emotion
                        best_intensity = score

    # 标点修正：感叹号增加强度
    if best_intensity > 0:
        exclam_count = content.count("!") + content.count("！")
        if exclam_count >= 2:
            best_intensity = min(10, best_intensity + 2)
        elif exclam_count == 1:
            best_intensity = min(10, best_intensity + 1)

    return {
        "label": best_emotion,
        "intensity": best_intensity,
        "matched_keywords": list(set(matched))[:5],  # 去重 + 限制返回数量
        "label_cn": EMOTION_CN.get(best_emotion, "未知"),
    }


def build_emotion_prompt(emotion: dict) -> str:
    """根据情绪生成共情指令，追加到 system prompt

    分 3 档：
    - intensity >= 7 (强)：必共情 + 必转人工
    - intensity >= 4 (中)：必共情
    - intensity < 4   (轻/无)：保持友好即可
    """
    if emotion["intensity"] < 4:
        return ""

    label_cn = emotion["label_cn"]
    intensity = emotion["intensity"]

    if intensity >= 7:
        return f"""

# 🚨 情绪预警（必读）
检测到用户当前情绪：**{label_cn}（强度 {intensity}/10）**
触发关键词：{emotion['matched_keywords']}

**强制要求**（按此顺序）：
1. **第一句必须共情**：用"非常抱歉给您带来不好的体验，完全理解您的感受 🙏"类似话术（不要带感叹号或卖萌 emoji）
2. **第二句简短说明事实**（如果有 RAG 资料或工具结果就引用，没有就承认）
3. **第三段主动提供升级**："如果以上方案不能让您满意，我可以立即为您转接人工客服处理"
4. 整体语气**温和、克制、不解释规则**，先认同情绪比讲道理重要 100 倍
"""

    # intensity 4-6
    return f"""

# ℹ️ 情绪提示
检测到用户情绪：**{label_cn}（强度 {intensity}/10）**

**要求**：回答开头**先用一句话共情**（如"理解您的心情"），再给方案。语气友好克制。
"""
