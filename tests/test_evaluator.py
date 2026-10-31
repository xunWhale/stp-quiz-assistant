"""Tests for AnswerEvaluator scoring and keyword matching."""

import pytest

from stp_quiz.evaluator import AnswerEvaluator
from stp_quiz.models import KeyPoint, Question, QuestionType, Category
from stp_quiz.question_bank import QuestionBank


@pytest.fixture
def question_bank():
    return QuestionBank()


def test_empty_answer(question_bank):
    q = question_bank.get("RSTP-PA-01")
    assert q is not None

    res1 = AnswerEvaluator.evaluate(q, "")
    assert res1.score == 0.0
    assert not res1.passed
    assert "黑子" in res1.feedback

    res2 = AnswerEvaluator.evaluate(q, "   \n\t  ")
    assert res2.score == 0.0
    assert not res2.passed


def test_choice_scoring(question_bank):
    q = question_bank.get("STP-ELEC-02")  # Answer: B
    assert q is not None

    # Correct lowercase
    res = AnswerEvaluator.evaluate(q, "b")
    assert res.score == 100.0
    assert res.passed

    # Correct with spaces
    res = AnswerEvaluator.evaluate(q, "  B  ")
    assert res.score == 100.0
    assert res.passed

    # Wrong
    res = AnswerEvaluator.evaluate(q, "A")
    assert res.score == 0.0
    assert not res.passed
    assert "已被加入错题本" in res.feedback


def test_multi_choice_scoring(question_bank):
    q = question_bank.get("PORT-ROLE-02")  # Answer: A,B,D
    assert q is not None

    # Exact match different formats
    res1 = AnswerEvaluator.evaluate(q, "A,B,D")
    assert res1.score == 100.0
    assert res1.passed

    res2 = AnswerEvaluator.evaluate(q, "dba")
    assert res2.score == 100.0
    assert res2.passed

    # Missed one option (Partial score)
    res_part = AnswerEvaluator.evaluate(q, "A,B")
    assert res_part.score == pytest.approx(66.7, 0.1)
    assert res_part.passed  # >= 60
    assert "漏选" in res_part.feedback

    # Selected wrong option C
    res_wrong = AnswerEvaluator.evaluate(q, "A,B,C,D")
    assert res_wrong.score == 0.0
    assert not res_wrong.passed
    assert "含错误选项" in res_wrong.feedback


def test_rstp_pa_mechanism_full_score(question_bank):
    q = question_bank.get("RSTP-PA-01")
    assert q is not None

    full_answer = (
        "RSTP 的 P/A 机制必须在点对点全双工链路运行。"
        "指定端口在 Discarding 状态发送置位 Proposal 标志的 BPDU 发起提案；"
        "下游交换机收到后执行 Sync 同步操作，阻塞除边缘端口外的所有非边缘端口防止临时环路；"
        "下游同步完成后，根端口回复置位 Agreement 标志的 BPDU；"
        "DP收到后立即切换到 Forwarding 转发状态，无需等待 30 秒的 Forward Delay 计时器。"
    )

    result = AnswerEvaluator.evaluate(q, full_answer)
    assert result.score == 100.0
    assert result.passed
    assert len(result.matched_points) == 5
    assert len(result.missed_points) == 0
    assert "S级表现" in result.feedback


def test_rstp_pa_mechanism_missing_required_sync(question_bank):
    q = question_bank.get("RSTP-PA-01")
    assert q is not None

    # Missing sync/blocking step completely
    partial_answer = (
        "RSTP P/A 在点对点全双工链路上运行。"
        "指定端口发送 Proposal，对端根端口回复 Agreement，然后立即进入 Forwarding 转发状态，不用等待 30 秒。"
    )

    result = AnswerEvaluator.evaluate(q, partial_answer)
    # Required key point "sync_blocking_action" is missed!
    assert not result.passed
    assert result.score <= 55.0
    assert any("Sync" in m or "同步" in m for m in result.missed_points)
    assert "核心硬性要点缺失" in result.feedback


def test_stp_election_essay_scoring(question_bank):
    q = question_bank.get("STP-ELEC-01")
    assert q is not None

    answer = (
        "STP 生成树选举依次按照以下四步判定：\n"
        "1. 比较全网最小的 Root BID（根桥ID，由优先级和MAC组成）选出根桥；\n"
        "2. 比较非根桥到达根桥的最小根路径开销（RPC）；\n"
        "3. 比较对端最小的 Sender BID（发送者桥ID）；\n"
        "4. 比较最小的 Sender PID（发送者端口ID，由端口优先级和端口号组成）。"
    )

    result = AnswerEvaluator.evaluate(q, answer)
    assert result.score == 100.0
    assert result.passed
    assert len(result.matched_points) == 4


def test_mstp_instance_essay_scoring(question_bank):
    q = question_bank.get("MSTP-INST-01")
    assert q is not None

    answer = (
        "MSTP 划分在同一个 MST Region 的三要素是：域名（Region Name）、修订级别（Revision Level）以及 VLAN 到 MSTI 实例映射关系一致。"
        "它的核心意义在于将多个 VLAN 映射捆绑到少量的 MSTI 实例中，既避免了普通 STP 单生成树无法负载分担的缺陷，"
        "又避免了 PVST 每 VLAN 一棵树导致交换机 CPU 资源和 BPDU 开销过大的问题，完美实现了多 VLAN 的负载均衡与资源节约。"
    )

    result = AnswerEvaluator.evaluate(q, answer)
    assert result.score >= 90.0
    assert result.passed


def test_port_states_essay_scoring(question_bank):
    q = question_bank.get("PORT-STATE-01")
    assert q is not None

    answer = (
        "STP 包括 Disabled、Blocking、Listening、Learning 和 Forwarding 5 种状态。"
        "RSTP 将其精简为 Discarding、Learning、Forwarding 3 种状态。"
        "Discarding 状态合并替代了 STP 的 Disabled、Blocking 和 Listening 状态。"
        "在行为上，Discarding 不转发数据也不学习 MAC 地址表，Learning 只学习 MAC 不转发流量，Forwarding 既转发数据又学习 MAC。"
    )

    result = AnswerEvaluator.evaluate(q, answer)
    assert result.score == 100.0
    assert result.passed
    assert len(result.matched_points) == 4


def test_question_without_key_points():
    q = Question(
        id="CUSTOM-01",
        category=Category.COMPREHENSIVE,
        qtype=QuestionType.ESSAY,
        title="Custom Question",
        content="Describe something",
        key_points=[],
    )
    result = AnswerEvaluator.evaluate(q, "Any answer provided")
    assert result.score == 100.0
    assert result.passed


def test_unknown_question_type():
    q = Question(
        id="CUSTOM-02",
        category=Category.COMPREHENSIVE,
        qtype="invalid_type",  # type: ignore
        title="Invalid",
        content="Invalid",
    )
    with pytest.raises(ValueError, match="Unknown question type"):
        AnswerEvaluator.evaluate(q, "answer")
