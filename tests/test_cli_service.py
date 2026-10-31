"""Tests for QuizService and CLI invocation."""

from pathlib import Path
import pytest

from stp_quiz.cli import create_parser, main
from stp_quiz.models import Category, QuestionType
from stp_quiz.question_bank import QuestionBank
from stp_quiz.service import QuizService
from stp_quiz.storage import Storage


@pytest.fixture
def service(tmp_path: Path):
    db_path = tmp_path / "svc_test.db"
    storage = Storage(db_path=db_path)
    return QuizService(storage=storage)


def test_service_quiz_and_submit_workflow(service: QuizService):
    # Draw question
    q = service.draw_question(category="stp_election", qtype="choice")
    assert q is not None
    assert q.id == "STP-ELEC-02"

    # Format card
    card = service.format_quiz_card(q, target_user="ikun-999")
    assert "ikun-999" in card
    assert "STP-ELEC-02" in card

    # Submit wrong answer first
    eval_res, user, wrong = service.submit_answer(
        user_id="ikun-999",
        question_id=q.id,
        answer="C",
    )
    assert not eval_res.passed
    assert eval_res.score == 0.0
    assert wrong is not None
    assert wrong.status == "pending"

    # Check pending list
    wrongs = service.get_user_pending_wrongs("ikun-999")
    assert len(wrongs) == 1

    # Now retest with correct answer
    eval_retest, user_retest, _ = service.submit_answer(
        user_id="ikun-999",
        question_id=q.id,
        answer="B",
        is_retest=True,
        wrong_record_id=wrong.id,
    )
    assert eval_retest.passed
    assert eval_retest.score == 100.0

    # Wrong record should now be resolved
    remaining_wrongs = service.get_user_pending_wrongs("ikun-999")
    assert len(remaining_wrongs) == 0

    # Format eval report
    report = service.format_eval_report(q, eval_retest, user_retest, is_retest=True)
    assert "补考通过！成功消题！" in report


def test_cli_subcommands(tmp_path: Path, capsys):
    db_file = str(tmp_path / "cli_test.db")

    # 1. list-questions
    main(["--db", db_file, "list-questions"])
    captured = capsys.readouterr()
    assert "题库题目列表" in captured.out
    assert "RSTP-PA-01" in captured.out

    # 2. quiz
    main(["--db", db_file, "quiz", "--qid", "STP-ELEC-02", "--user", "tester"])
    captured = capsys.readouterr()
    assert "STP-ELEC-02" in captured.out
    assert "tester" in captured.out

    # 3. submit wrong answer
    main([
        "--db", db_file,
        "submit",
        "--user", "tester",
        "--qid", "STP-ELEC-02",
        "--answer", "D",
    ])
    captured = capsys.readouterr()
    assert "考核翻车" in captured.out

    # 4. wrong-list
    main(["--db", db_file, "wrong-list", "tester"])
    captured = capsys.readouterr()
    assert "STP-ELEC-02" in captured.out

    # 5. leaderboard
    main(["--db", db_file, "leaderboard"])
    captured = capsys.readouterr()
    assert "tester" in captured.out

    # 6. export-data
    json_path = str(tmp_path / "backup.json")
    main(["--db", db_file, "export-data", json_path])
    captured = capsys.readouterr()
    assert "成功将数据备份导出至" in captured.out
    assert Path(json_path).exists()

    # 7. import-data to another db
    db2 = str(tmp_path / "cli_test2.db")
    main(["--db", db2, "import-data", json_path])
    captured = capsys.readouterr()
    assert "成功从" in captured.out


def test_cli_interactive_inspect(monkeypatch, tmp_path: Path, capsys):
    db_file = str(tmp_path / "inspect_test.db")
    # Simulate user answering "B" to choice question
    monkeypatch.setattr("builtins.input", lambda prompt="": "B")

    main(["--db", db_file, "inspect", "student_ikun", "--qid", "STP-ELEC-02"] if False else [
        "--db", db_file, "inspect", "student_ikun", "--category", "stp_election", "--type", "choice"
    ])
    captured = capsys.readouterr()
    assert "student_ikun" in captured.out
    assert "考核通过" in captured.out


def test_cli_interactive_retest_and_menu(monkeypatch, tmp_path: Path, capsys):
    db_file = str(tmp_path / "retest_test.db")
    storage = Storage(db_path=db_file)
    service = QuizService(storage=storage)

    # First add a wrong record
    service.submit_answer(user_id="retest_user", question_id="STP-ELEC-02", answer="A")
    assert len(service.get_user_pending_wrongs("retest_user")) == 1

    # Retest interactive with correct answer
    inputs = iter(["B"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    main(["--db", db_file, "retest", "retest_user"])
    captured = capsys.readouterr()
    assert "补考通过！成功消题！" in captured.out
    assert len(service.get_user_pending_wrongs("retest_user")) == 0

    # Retest when no wrongs left
    main(["--db", db_file, "retest", "retest_user"])
    captured = capsys.readouterr()
    assert "没有未补错题" in captured.out

    # Test interactive menu exit (choice "0")
    menu_inputs = iter(["0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(menu_inputs))
    main(["--db", db_file, "interactive"])
    captured = capsys.readouterr()
    assert "拜拜咯" in captured.out
