"""项目的静态数据定义（如枚举、常量）

当前包含：MBTI 的 16 种类型定义，供项目其余模块引用。
"""

# 不变的 MBTI 类型元组（用于 membership 测试）
MBTI_TYPES = (
    "INTJ","INTP","ENTJ","ENTP","INFJ","INFP","ENFJ","ENFP",
    "ISTJ","ISFJ","ESTJ","ESFJ","ISTP","ISFP","ESTP","ESFP",
)

# 方便用于 random.choice 的列表
MBTI_LIST = list(MBTI_TYPES)


def is_valid_mbti(s: str) -> bool:
    """判断字符串是否为合法 MBTI 值。"""
    return s in MBTI_TYPES
