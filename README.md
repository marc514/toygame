# Toy Game

这是一个简单的 Python 小项目，实现了 Pet、触发器（Trigger）以及数据库持久化。项目包含主函数和 pytest 测试。

功能亮点：

- 在主函数中创建多个 `Pet` 实例，随机分配出生日期与性别，存入 SQLite 数据库。
- 抽象 `Trigger` 基类，并实现了 `BirthTrigger`（当天生日触发）和若干 `TimerTrigger`（例如 `DinnerTimer` 在 18:00 触发）。
- 当触发器触发时，数据库会把触发发生的时间以 ISO 格式追加到该 `Pet` 的对应触发器时间历史（JSON 列）中，保留完整触发记录，而不是仅仅计数。

安装依赖：

```bash
# 运行时依赖（当前项目仅使用标准库，通常为空）
python -m pip install -r requirements.txt

# 开发与测试依赖（用于运行测试、收集覆盖率等）
python -m pip install -r requirements-dev.txt
```

运行测试：

```bash
pytest -q
```

运行主程序：

```bash
python -m toygame.main
```

