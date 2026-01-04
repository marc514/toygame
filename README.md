# Toy Game

这是一个简单的 Python 小项目，实现了 Pet、触发器（Trigger）以及数据库持久化。项目包含主函数和 pytest 测试。

功能亮点：

- 在主程序（`python -m toygame.main`）中演示：先使用 `create_pets` 创建若干 `Pet`（每个含 MBTI 属性），再调用 `run_game` 对数据库中的宠物轮询触发器并记录触发时间。
- 抽象 `Trigger` 基类，并实现了 `BirthTrigger`（当天生日触发）和若干 `TimerTrigger`（例如 `DinnerTimer` 在 18:00 触发）。
- 当触发器触发时，数据库会把触发发生的时间以 ISO 格式追加到该 `Pet` 的对应触发器时间历史（JSON 列）中，保留完整触发记录，而不是仅仅计数。
- 注意：`DB` 在初始化时会 DROP & CREATE `pets` 表以使用最新 schema（会清除旧数据），
  此为有意的简化设计，请在生产或长期数据场景中慎用或提供迁移策略；
- 触发规则：同一只 `Pet` 的同一触发器在同一天仅记录一次（即“每日一次”规则）。

安装依赖：

```bash
# 运行时依赖
conda create -n game python=3.12.1
conda activate game
python -m pip install -r requirements.txt
```

运行测试：

```bash
# 主流程
pytest tests/test_game.py::test_run_game_multiple_times_with_time_progression -q -s
# 全部单测
pytest -q
# 可以在pytest默认tmp路径下查看test.db，人工校验
```

运行主程序：

```bash
python -m toygame.main
```

