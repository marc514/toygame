import asyncio
import os
import pytest

from toygame.db import DB
from toygame.events import GeminiAPIEvent
from toygame.models import Pet


def test_gemini_api_event_execute_with_real_api(tmp_path, monkeypatch):
    """测试GeminiAPIEvent执行方法，使用真实的Gemini API调用"""
    # 从环境变量获取API密钥，如果不存在则跳过测试
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY环境变量未设置，跳过真实API调用测试")

    # 创建测试数据
    dbfile = tmp_path / "test.db"
    # 可以提供一个已存在的数据库文件路径，用于测试
    dbfile = "/data/toygame/pets.db"
    db = DB(str(dbfile))
    # 如果数据库中没有id为1的宠物，就创建一个
    pets = db.get_pets(pet_ids=[1])
    if not pets:  # 检查列表是否为空，而不是检查是否为None
        pet = db.add_pet(
            Pet(
                id=None,
                name="TestPet1",
                birth_date="2023-01-01",
                gender="M",
                mbti="INTJ",
            )
        )
    else:
        pet = pets[0]

    # 创建事件实例，使用真实API密钥
    event = GeminiAPIEvent(api_key=api_key)

    # 设置触发器名称
    trigger_name = "test_trigger"

    # 执行事件
    result = asyncio.run(event.execute(trigger_name, pet, db))

    # 验证结果
    assert result is True, "API调用应该成功"
