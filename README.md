# Toy Game

这是一个简单的 Python 小项目，实现了 Pet、触发器（Trigger）以及数据库持久化。项目包含主函数和 pytest 测试。

功能亮点：

- 在主函数中创建多个 `Pet` 实例，随机分配出生日期与性别，存入 SQLite 数据库。
- 抽象 `Trigger` 基类，并实现了 `BirthTrigger`（当天生日触发）和 `TimerTrigger`（6pm 触发）。
- 当触发器触发时，数据库会相应地对该 `Pet` 的触发计数进行 ++。

运行测试：

```bash
pytest -q
```

运行主程序：

```bash
python -m toygame.main
```

如果需要我可以：
- 添加更多触发器类型或更复杂的条件
- 添加命令行参数以自定义宠物数量或时间
