# stp-quiz-assistant（ikun群 STP 抽查小助手）

> **作者 / 署名**：xunWhale  
> **版本**：v1.0.0  
> **项目定位**：面向网络工程师群聊（ikun 群）打造的 STP / RSTP / MSTP 生成树协议突击抽查、智能判分与错题本补考管理小助手。

---

## 📖 项目简介

在网络工程师的技术交流群（尤其是热衷于高阶协议推演与技术内卷的 ikun 群）中，生成树协议（STP / RSTP / MSTP）一直是面试、CCIE/HCIE 认证以及现网排障的常考重难点。然而，传统的刷题和问答往往存在以下痛点：
1. **人工判分繁琐**：尤其是机制分析简答题（如 RSTP 的 Proposal/Agreement 握手、拓扑同步 Sync 阻塞机制），难以量化考核要点；
2. **缺乏错题闭环**：群友答错后容易直接遗忘，缺乏待补考队列和消错机制；
3. **缺少积分激励**：缺少积分榜、答题胜率统计与群友战力排行。

**stp-quiz-assistant** 针对上述场景设计，既可作为独立的 Python CLI 工具供个人自测与练习，也可作为 Python SDK 轻松嵌入各类群聊机器人（如 OneBot、NoneBot、飞书、钉钉、企微机器人等）。

---

## 🌟 核心特性

### 1. 专业高质量生成树题库
内置覆盖全面、考点深入的 STP/RSTP/MSTP 题库：
- **STP 选举机制**：Root Bridge 选举、根路径开销（RPC）、Sender BID、Sender PID（含对端与本地 PID 判定陷阱）；
- **端口角色与状态迁移**：STP 5 种状态（Disabled, Blocking, Listening, Learning, Forwarding）与 RSTP 3 种状态（Discarding, Learning, Forwarding）对比，Alternate、Backup、Edge Port 角色判定；
- **RSTP 快速收敛与 Proposal/Agreement（P/A）机制**：点对点全双工前提、DP 发起 Proposal、下游 Sync 同步阻塞所有非边缘端口防止临时环路、RP 回复 Agreement、秒级切入 Forwarding 跳过 30s 计时器；
- **MSTP 实例映射与区域三要素**：Format Selector / Region Name / Revision Level / VLAN-to-Instance 映射、CST / IST / CIST 拓扑层次；
- **经典易错拓扑推演**：双交换机多直连链路下的 RP 端口推导题（深度考察 Sender PID 判定顺序）。

### 2. 智能多维度判分引擎（AnswerEvaluator）
- **客观题精准校验**：单选与多选题支持模糊输入过滤（如 `A,B`、`abd`、`b a` 自动归一化）；多选题支持漏选部分分与误选 0 分惩罚机制；
- **主观题要点拆解评分**：
  - **核心概念分块（Key Points）**：将复杂机制拆分为若干独立要点，支持中英文双语与技术别名（如 `Point-to-Point` / `p2p` / `点对点`、`Sync` / `同步`、`Discarding` / `阻塞`）；
  - **硬性必答项（Required Point）**：对关键防环机制（如 P/A 中的 Sync 阻塞非边缘端口）设置必答红线，若未答到则成绩封顶（< 60分），防止出现“懂大概却遗漏关键防环机制”的侥幸及格；
  - **个性化诊断反馈**：逐条列出【命中要点】、【缺失要点】与深入的标准解析，并配有 ikun 特色趣味评语。

### 3. 群友积分体系与错题本消错闭环（Storage）
- 基于 SQLite 本地持久化，支持跨平台零外部依赖；
- **错题本管理**：答题未通过（< 60分）自动进入 `wrong_records` 表，状态置为 `pending`；
- **补考消题机制**：支持发起专项补考，答对后记录订正时间并自动消题（状态转为 `resolved`）；
- **风云榜单**：支持按群友总分、刷题量、及格通过率多维度生成天梯排行榜；
- **数据无损备份**：提供 `export-data` 与 `import-data`，支持与 JSON 格式双向导入导出。

### 4. 丰富多样的 CLI 与交互模式
- 支持命令行一次性快速调用（方便脚本和机器人集成）；
- 支持突击抽查指定群友（`inspect`）；
- 支持针对个人的待补考错题订正（`retest`）；
- 提供沉浸式全交互控制台（`interactive`）。

---

## 🏗️ 系统架构

```
stp-quiz-assistant/
├── pyproject.toml              # 项目打包与依赖配置 (Console Scripts: stp-quiz)
├── stp_quiz/
│   ├── __init__.py             # 模块入口与版本元数据
│   ├── __main__.py             # 支持 python3 -m stp_quiz 运行
│   ├── cli.py                  # CLI 命令行入口与交互控制台
│   ├── models.py               # Question, KeyPoint, EvalResult, UserRecord, WrongRecord 数据模型
│   ├── question_bank.py        # 题库管理、多维过滤、随机抽题、导入导出
│   ├── questions.json          # 预置题库 JSON 备份与扩展包
│   ├── evaluator.py            # 智能判分与关键词权重评分引擎
│   ├── storage.py              # SQLite 存储层 (群友积分、错题本、历史记录、JSON 备份)
│   └── service.py              # 业务编排层 (出题、判题、补考、生成通报报告)
└── tests/
    ├── test_question_bank.py   # 题库管理单元测试
    ├── test_evaluator.py       # 判分引擎与关键词/要点测试
    ├── test_storage.py         # 存储层、积分与错题本测试
    └── test_cli_service.py     # CLI 交互与业务服务单元测试
```

---

## 🚀 快速上手与 CLI 使用方法

### 1. 安装项目

可以使用 pip 进行可编辑安装（Editable Mode）：
```bash
cd /home/fish/stp-quiz-assistant
pip install -e .
```
或者直接使用 `python3 -m stp_quiz` 运行，无需额外依赖（仅依赖 Python 3.9+ 标准库）。

---

### 2. 常用命令行示例

#### (1) 查看题库所有考点
```bash
stp-quiz list-questions
```
输出示例：
```text
📚 题库题目列表 (共 9 道):
ID              分类                    题型            难度      标题
---------------------------------------------------------------------------
STP-ELEC-01     stp_election          essay         ★★★     STP 根桥及端口角色四步选举机制
STP-ELEC-02     stp_election          choice        ★★      STP 桥优先级配置步长与默认值
PORT-STATE-01   port_roles_states     essay         ★★★     STP 5种端口状态与 RSTP 3种端口状态的映射与区别
PORT-ROLE-02    port_roles_states     multi_choice  ★★★     RSTP 新增端口角色及其防护功能
RSTP-PA-01      rstp_convergence_pa   essay         ★★★★    RSTP Proposal/Agreement (P/A) 快速收敛握手机制深度剖析
RSTP-EDGE-01    rstp_convergence_pa   choice        ★★★     RSTP 边缘端口（Edge Port）的特性与行为
MSTP-INST-01    mstp_instance         essay         ★★★★    MSTP 区域三要素与 VLAN 到 MSTI 实例映射原理
MSTP-CONV-02    mstp_instance         choice        ★★★     MSTP 树概念：CST, IST 与 CIST 的拓扑层次关系
COMP-TOPO-01    comprehensive         essay         ★★★★    经典双交换机多链路拓扑下的根端口（RP）选举推演
---------------------------------------------------------------------------
```

#### (2) 随机抽题自测 / 指定题号出题
```bash
# 随机抽取一道考题
stp-quiz quiz

# 抽取指定分类的考题
stp-quiz quiz --category rstp_convergence_pa

# 指定题号直接出题
stp-quiz quiz --qid RSTP-PA-01 --user "kun_kun"
```

#### (3) 提交作答并获取智能判分报告
```bash
stp-quiz submit \
  --user "kun_kun" \
  --qid "RSTP-PA-01" \
  --answer "RSTP的PA机制必须在点对点全双工链路运行。指定端口DP处于Discarding向对端发Proposal，下游交换机收到后立刻执行Sync同步，阻塞所有非边缘端口以防止环路，随后根端口回复Agreement，DP收到后立即进入Forwarding状态，不用等待30秒Forward Delay计时器。"
```
**输出报告：**
```text
============================================================
【STP 抽查判分结果通报】🎉 考核通过
👤 答题群友: kun_kun (ID: kun_kun)
🎯 本题得分: 100.0 分 (及格线: 60.0 分)
📊 群友总分: 100.0 分 | 答题数: 1 | 通过率: 100.0%
------------------------------------------------------------
✅ 【命中核心要点】:
   • 必须在点对点（Point-to-Point）链路且全双工（Full-Duplex）环境下才能启用 P/A 机制 (命中词: 点对点, 全双工)
   • 指定端口（DP）在 Discarding 状态发送置位 Proposal 的 BPDU 发起提议 (命中词: proposal, 指定端口)
   • 下游设备执行 Sync 同步，阻塞（Discarding）所有非边缘端口以杜绝临时环路 (命中词: sync, 阻塞, 非边缘)
   • 下游同步完成后，根端口（RP）回复置位 Agreement 标志的 BPDU (命中词: agreement, 根端口)
   • 收到 Agreement 后 DP 立即进入 Forwarding 状态，无需等待 30 秒 Forward Delay 计时器 (命中词: forwarding, 不用等待)
------------------------------------------------------------
💬 【判分评语】:
   【S级表现 / 得分: 100.0】完美解析！核心要点全面覆盖，ikun 顶流网络攻城狮就是你！
------------------------------------------------------------
📖 【标准解析与考点精讲】:
   P/A 机制是 RSTP 实现极速收敛的灵魂。通过点对点的主动握手与 Sync 阻塞机制，避免了传统 STP 死板依靠 2*Forward Delay(30s) 定时器来防环的缺陷。
============================================================
```

#### (4) 突击抽查指定群友（交互答题）
```bash
stp-quiz inspect "小黑子群友"
```

#### (5) 查看群友待补考错题列表
```bash
# 查看所有人的未消错题
stp-quiz wrong-list

# 查看指定群友的未消错题
stp-quiz wrong-list "小黑子群友"
```

#### (6) 发起错题补考（答对即可消题）
```bash
stp-quiz retest "小黑子群友"
```

#### (7) 查看群友积分天梯榜
```bash
stp-quiz leaderboard --limit 10
```

#### (8) 备份与迁移数据（JSON 导入导出）
```bash
# 导出当前数据到 JSON 备份文件
stp-quiz export-data my_backup.json

# 从备份 JSON 恢复导入到新的数据库
stp-quiz import-data my_backup.json --db /path/to/new.db
```

#### (9) 进入沉浸式交互控制台
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

本项目采用 `pytest` 编写全套测试用例，覆盖题库加载、判分要点、错题生命周期、补考消题及 CLI 各命令：

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
tests/test_evaluator.py::test_question_without_key_points PASSED
tests/test_evaluator.py::test_unknown_question_type PASSED
tests/test_question_bank.py::test_question_bank_defaults PASSED
tests/test_question_bank.py::test_filter_and_pick_random PASSED
tests/test_question_bank.py::test_export_and_import_json PASSED
tests/test_storage.py::test_user_creation_and_stats PASSED
tests/test_storage.py::test_wrong_record_and_resolve PASSED
tests/test_storage.py::test_leaderboard PASSED
tests/test_storage.py::test_json_backup_and_restore PASSED
============================== 21 passed in 0.38s ==============================
```

---

## 📄 许可证与署名

- **作者**：xunWhale
- **协议**：MIT License
