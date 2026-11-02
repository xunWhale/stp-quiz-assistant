# stp-quiz-assistant

> **作者 / 署名**：xunWhale  
> **版本**：v1.0.0  
> **项目定位**：面向网络工程领域打造的 STP / RSTP / MSTP 生成树协议突击抽查、智能判分与错题本补考管理小助手。

---

## 📖 项目简介

在网络工程师的技术交流群（尤其是协议推演与现网架构场景）中，生成树协议（STP / RSTP / MSTP）一直是面试、CCIE/HCIE 认证以及现网排障的常考重难点。然而，传统的刷题和问答往往存在以下痛点：
1. **人工判分繁琐**：尤其是机制分析简答题（如 RSTP 的 Proposal/Agreement 握手、拓扑同步 Sync 阻塞机制），难以量化考核要点；
2. **缺乏错题闭环**：群友答错后容易直接遗忘，缺乏待补考队列和消错机制；
3. **缺少积分激励**：缺少积分榜、答题胜率统计与群友战力排行。

**stp-quiz-assistant** 针对上述场景设计，既可作为独立的 Python CLI 工具供个人自测与练习，也可作为 Python SDK 轻松嵌入各类群聊机器人（如 OneBot、NoneBot、飞书、钉钉、企微机器人等）。

---

## 🌟 核心特性

### 1. 专业高质量生成树题库
内置覆盖全面、考点深入的 STP/RSTP/MSTP 题库（共 14 道精选考题），支持多种题型（客观单选/多选、机制简答论述、拓扑计算判断、分析补全）：
- **STP 选举机制**：Root Bridge 选举、根路径开销（RPC）、Sender BID、Sender PID（含对端与本地 PID 判定陷阱）；
- **PID / BID 数值计算与 802.1t 开销**：Bridge Priority 与 VLAN 扩展 ID 组合计算、PID 构成、802.1t 链路开销（100M/1G/10G）；
- **Forward Delay 计时器机制**：15 秒设计机理（Listening 防环、Learning 学习 MAC 防泛洪）、TC BPDU 触发下 MAC 地址老化时间由 300 秒强制缩短至 15 秒（Forward Delay）；
- **端口角色与状态迁移**：STP 5 种状态（Disabled, Blocking, Listening, Learning, Forwarding）与 RSTP 3 种状态（Discarding, Learning, Forwarding）对比；
- **Alternate 与 Backup 端口深度辨析**：Alternate 备 RP（收到对端更优 BPDU 阻塞）、Backup 备 DP（收到本交换机更优 BPDU 阻塞，常见于 Hub 共享总线或自环）；
- **RSTP 快速收敛与 Proposal/Agreement（P/A）机制**：点对点全双工前提、DP 发起 Proposal、下游 Sync 同步阻塞所有非边缘端口防止临时环路、RP 回复 Agreement、秒级切入 Forwarding 跳过 30s 计时器；
- **Edge Port 边缘端口特性**：直连终端直接转发、收 BPDU 丧失边缘属性/触发 BPDU 保护、Up/Down 不发送 TC BPDU；
- **MSTP 实例映射与区域三要素**：Format Selector / Region Name / Revision Level / VLAN-to-Instance 映射、CST / IST / CIST 拓扑层次；
- **经典三角环网与双交换机拓扑推演**：多链路直连与三角形环网下的根端口、指定端口与阻塞端口推导。

### 2. 智能多维度判分引擎（AnswerEvaluator / Grader）
- **客观题精准校验**：单选与多选题支持模糊输入过滤（如 `A,B`、`abd`、`b a` 自动归一化）；多选题支持漏选部分分与误选 0 分惩罚机制；
- **主观题与拓扑题要点拆解评分**：
  - **核心概念分块（Key Points）**：将复杂机制拆分为若干独立要点，支持中英文双语与技术别名（如 `Point-to-Point` / `p2p` / `点对点`、`Sync` / `同步`、`Discarding` / `阻塞`）；
  - **硬性必答项（Required Point）**：对关键防环机制（如 P/A 中的 Sync 阻塞非边缘端口）设置必答红线，若未答到则成绩封顶（< 60分），防止出现“懂大概却遗漏关键防环机制”的侥幸及格；
  - **个性化诊断反馈**：逐条输出【得分】、【命中要点】、【缺失要点】、【错误点分析】、【未掌握知识点标签】、【标准解析】与【补考建议】。
- **分析补全题精准槽位核验**：支持序号空位匹配与关键词自动提取，按空位命中率准确折算分值。

### 3. 群友积分体系、欠考查账与错题本消错闭环（Storage / Tracker）
- 基于 SQLite 本地持久化，支持跨平台零外部依赖；
- **错题本管理**：答题未通过（< 60分）自动进入 `wrong_records` 表，状态置为 `pending`，并自动被打上未掌握知识点标签（如「RSTP P/A机制未掌握」）；
- **群友欠考查账（Audit）**：一键生成群友技术画像账本，清晰列出累计欠考题数、详细错题清单、未掌握标签画像与及格率；
- **补考消题机制**：支持针对个人的未消错题一键生成专属 100 分补考卷，答对后记录订正时间并自动消题（状态转为 `resolved`）；
- **风云榜单**：支持按群友总分、刷题量、及格通过率多维度生成天梯排行榜；
- **数据无损备份**：提供 `export-data` 与 `import-data`，支持与 JSON 格式双向导入导出。

### 4. 丰富多样的 CLI 与交互模式
- **抽查生成（paper）**：一键随机或针对群友弱项生成一份均衡覆盖 100 分综合抽查卷；
- **批改交卷（grade-paper）**：输入整卷作答，秒级输出成绩单；
- **查账与补考（audit / retest-paper）**：查询群友（如月月鸟）的欠考账本与专属补考卷；
- **沉浸式交互控制台（interactive）**：终端可视化菜单全流程闭环。

---

## 🏗️ 系统架构

```
stp-quiz-assistant/
├── pyproject.toml              # 项目打包与依赖配置 (Console Scripts: stp-quiz)
├── stp-quiz                    # CLI 可执行快捷脚本
├── stp_quiz/
│   ├── __init__.py             # 模块入口、全功能导出与版本元数据
│   ├── __main__.py             # 支持 python3 -m stp_quiz 运行
│   ├── cli.py                  # CLI 命令行入口与全功能交互控制台
│   ├── models.py               # Question, KeyPoint, EvalResult, QuizPaper, PaperScoreReport 模型
│   ├── question_bank.py        # 题库管理、多维过滤、随机抽题、JSON 导入导出
│   ├── questions.json          # 预置题库 JSON 完整备份
│   ├── evaluator.py            # 智能判分与关键词权重评分引擎 (AnswerEvaluator)
│   ├── grader.py               # 评分评估模块统一导出接口 (Grader)
│   ├── storage.py              # SQLite 存储层 (群友积分、错题本、试卷成绩单、JSON 备份)
│   ├── tracker.py              # 成绩与错题追踪模块统一导出接口 (QuizTracker)
│   ├── service.py              # 业务编排层 (出题、组卷、判卷、补考、查账)
│   └── assistant.py            # 助手业务模块统一导出接口 (Assistant)
└── tests/
    ├── test_question_bank.py   # 题库管理与核心知识点覆盖单元测试
    ├── test_evaluator.py       # 判分引擎与多题型评分单元测试
    ├── test_storage.py         # 存储层、积分与错题本单元测试
    ├── test_cli_service.py     # CLI 交互与业务服务单元测试
    └── test_paper_and_retest.py# 100分试卷生成、批改交卷、查账与补考卷专项测试
```

---

## 🚀 快速上手与 CLI 使用方法

### 1. 安装项目

可以使用 pip 进行可编辑安装（Editable Mode）：
```bash
cd /home/fish/stp-quiz-assistant
pip install -e .
```
或者直接使用 `./stp-quiz` 或 `python3 -m stp_quiz` 运行，无需额外系统依赖（仅依赖 Python 3.9+ 标准库）。

---

### 2. 常用命令行示例

#### (1) 生成一份 100 分综合抽查卷 (paper)
```bash
# 为群友“月月鸟”生成 100 分抽查试卷（支持根据弱项优先选题）
stp-quiz paper --user "月月鸟" --weak-first

# 生成并将试卷导出为 JSON 文件
stp-quiz paper --user "月月鸟" --out my_paper.json
```

#### (2) 整卷作答与智能批改生成成绩单 (grade-paper)
```bash
# 启动交互式逐题答卷模式，答完立即批改
stp-quiz grade-paper --user "月月鸟" --interactive

# 或直接传入作答 JSON 字典批改指定试卷文件
stp-quiz grade-paper --user "月月鸟" --paper-file my_paper.json --answers '{"STP-ELEC-02": "B", "RSTP-EDGE-01": "D"}'
```

#### (3) 群友欠考查账与未掌握画像 (audit)
```bash
# 查询月月鸟的历史抽查得分、欠考账本与未掌握知识点标签
stp-quiz audit "月月鸟"
```

#### (4) 生成专属错题补考卷 (retest-paper)
```bash
# 针对月月鸟的所有欠考错题生成专属 100 分补考卷
stp-quiz retest-paper "月月鸟"

# 直接在终端启动该补考卷的答题订正与消错
stp-quiz retest-paper "月月鸟" --interactive
```

#### (5) 查看题库所有考点清单
```bash
stp-quiz list-questions
```

#### (6) 随机抽单题自测 / 指定题号出题
```bash
# 随机抽取一道考题
stp-quiz quiz

# 抽取指定分类的考题（如 forward_delay_timers 或 rstp_convergence_pa）
stp-quiz quiz --category forward_delay_timers

# 指定题号直接出题
stp-quiz quiz --qid RSTP-PA-01 --user "月月鸟"
```

#### (7) 提交单题作答并获取智能判分报告
```bash
stp-quiz submit \
  --user "月月鸟" \
  --qid "RSTP-PA-01" \
  --answer "RSTP的PA机制必须在点对点全双工链路运行。指定端口DP处于Discarding向对端发Proposal，下游交换机收到后立刻执行Sync同步，阻塞所有非边缘端口以防止环路，随后根端口回复Agreement，DP收到后立即进入Forwarding状态，不用等待30秒Forward Delay计时器。"
```

#### (8) 查看未消错题列表
```bash
# 查看所有人的未消错题
stp-quiz wrong-list

# 查看指定群友的未消错题
stp-quiz wrong-list "月月鸟"
```

#### (9) 查看群友积分战力排行榜
```bash
stp-quiz leaderboard --limit 10
```

#### (10) 备份与迁移数据（JSON 导入导出）
```bash
# 导出当前数据到 JSON 备份文件
stp-quiz export-data my_backup.json

# 从备份 JSON 恢复导入到新的数据库
stp-quiz import-data my_backup.json --db /path/to/new.db
```

#### (11) 进入沉浸式交互控制台
```bash
stp-quiz interactive
```

---

## 🤖 Python API / 群聊机器人集成示例

在基于 NoneBot / Mirai / 飞书 SDK 的群聊机器人中，只需几行代码即可完成集成：

```python
from stp_quiz.service import QuizService
from stp_quiz.models import Category

# 初始化服务（默认数据库保存在 ~/.stp_quiz/stp_quiz.db）
service = QuizService()

# 1. 群内抽题并发送
question = service.draw_question(category="rstp_convergence_pa")
quiz_msg = service.format_quiz_card(question, target_user="群友张三")
# send_to_group(quiz_msg)

# 2. 接收群友回答并打分
user_answer = "P/A机制需要点对点全双工，DP发送Proposal，下游Sync阻塞非边缘端口，RP回复Agreement立即转发。"
eval_res, user_record, wrong_record = service.submit_answer(
    user_id="10001",
    question_id=question.id,
    answer=user_answer,
    nickname="群友张三"
)

# 3. 生成通报并发送
report_msg = service.format_eval_report(question, eval_res, user_record)
# send_to_group(report_msg)

# 4. 判断是否进入错题本
if not eval_res.passed:
    print(f"群友张三已挂科，错题记录ID: {wrong_record.id}，需提醒补考！")
```

---

## 🧪 单元测试

本项目采用 `pytest` 编写全套测试用例，覆盖题库加载、判分要点、错题生命周期、补考消题、100分试卷组卷、成绩单批改、群友查账及 CLI 各命令：

```bash
# 运行全部单元测试
pytest -v tests/
```

测试执行结果：
```text
tests/test_cli_service.py::test_service_quiz_and_submit_workflow PASSED
tests/test_cli_service.py::test_cli_subcommands PASSED
tests/test_cli_service.py::test_cli_interactive_inspect PASSED
tests/test_cli_service.py::test_cli_interactive_retest_and_menu PASSED
tests/test_evaluator.py::test_empty_answer PASSED
tests/test_evaluator.py::test_choice_scoring PASSED
tests/test_evaluator.py::test_multi_choice_scoring PASSED
tests/test_evaluator.py::test_rstp_pa_mechanism_full_score PASSED
tests/test_evaluator.py::test_rstp_pa_mechanism_missing_required_sync PASSED
tests/test_evaluator.py::test_stp_election_essay_scoring PASSED
tests/test_evaluator.py::test_mstp_instance_essay_scoring PASSED
tests/test_evaluator.py::test_port_states_essay_scoring PASSED
tests/test_evaluator.py::test_calc_bid_pid_scoring PASSED
tests/test_evaluator.py::test_triangle_topo_calc_scoring PASSED
tests/test_evaluator.py::test_alt_bp_port_roles_scoring PASSED
tests/test_evaluator.py::test_question_without_key_points PASSED
tests/test_evaluator.py::test_unknown_question_type PASSED
tests/test_paper_and_retest.py::test_question_bank_coverage PASSED
tests/test_paper_and_retest.py::test_evaluator_topo_calc_and_timers PASSED
tests/test_paper_and_retest.py::test_evaluator_analysis_fill PASSED
tests/test_paper_and_retest.py::test_generate_100pt_paper_and_grading PASSED
tests/test_paper_and_retest.py::test_audit_and_retest_paper PASSED
tests/test_paper_and_retest.py::test_cli_paper_audit_retest_commands PASSED
tests/test_question_bank.py::test_question_bank_defaults PASSED
tests/test_question_bank.py::test_filter_and_pick_random PASSED
tests/test_question_bank.py::test_export_and_import_json PASSED
tests/test_storage.py::test_user_creation_and_stats PASSED
tests/test_storage.py::test_wrong_record_and_resolve PASSED
tests/test_storage.py::test_leaderboard PASSED
tests/test_storage.py::test_json_backup_and_restore PASSED
============================== 30 passed in 0.61s ==============================
```

---

## 📄 许可证与署名

- **作者**：xunWhale
- **协议**：MIT License
