import pytest
from unittest.mock import Mock
import os
from toygame.events import GeminiAPIEvent
from toygame.models import Pet
from toygame.db import DB


def test_gemini_api_event_execute_with_real_api():
    """测试GeminiAPIEvent执行方法，使用真实的Gemini API调用"""
    # 从环境变量获取API密钥，如果不存在则跳过测试
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY环境变量未设置，跳过真实API调用测试")

    # 创建测试数据
    pet = Pet(id=1, name="TestPet", birth_date="2023-01-01", gender="M", mbti="INTJ")
    db = Mock(spec=DB)

    # 创建事件实例，使用真实API密钥
    event = GeminiAPIEvent(api_key=api_key)

    # 设置触发器名称
    trigger_name = "test_trigger"

    # 执行事件
    result = event.execute(trigger_name, pet, db)

    # 验证结果
    assert result is True, "API调用应该成功"
