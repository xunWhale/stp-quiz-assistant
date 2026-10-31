"""Tests for Storage layer with SQLite and JSON serialization."""

from pathlib import Path
import pytest

from stp_quiz.storage import Storage


@pytest.fixture
def test_storage(tmp_path: Path):
    db_file = tmp_path / "test_stp.db"
    return Storage(db_path=db_file)


def test_user_creation_and_stats(test_storage: Storage):
    user = test_storage.get_or_create_user("user1", "ikun-1号")
    assert user.user_id == "user1"
    assert user.nickname == "ikun-1号"
    assert user.total_score == 0.0
    assert user.total_quizzes == 0
    assert user.pass_rate == 0.0

    # Record first quiz (passed, 100)
    u_after1, wrong1 = test_storage.record_quiz_result(
        user_id="user1",
        question_id="Q1",
        question_title="Test Q1",
        user_answer="A",
        score=100.0,
        passed=True,
    )
    assert u_after1.total_score == 100.0
    assert u_after1.total_quizzes == 1
    assert u_after1.passed_quizzes == 1
    assert u_after1.pass_rate == 100.0
    assert wrong1 is None

    # Record second quiz (failed, 30)
    u_after2, wrong2 = test_storage.record_quiz_result(
        user_id="user1",
        question_id="Q2",
        question_title="Test Q2",
        user_answer="bad answer",
        score=30.0,
        passed=False,
    )
    assert u_after2.total_score == 130.0
    assert u_after2.total_quizzes == 2
    assert u_after2.passed_quizzes == 1
    assert u_after2.pass_rate == 50.0
    assert wrong2 is not None
    assert wrong2.status == "pending"


def test_wrong_record_and_resolve(test_storage: Storage):
    # Fail two questions for user2
    test_storage.record_quiz_result("user2", "Q1", "Title 1", "wrong", 0.0, False)
    test_storage.record_quiz_result("user2", "Q2", "Title 2", "wrong", 40.0, False)

    wrongs = test_storage.get_pending_wrong_records("user2")
    assert len(wrongs) == 2
    assert wrongs[0].question_id == "Q1"
    assert wrongs[1].question_id == "Q2"

    # Resolve first wrong record
    rec_id = wrongs[0].id
    assert rec_id is not None
    resolved = test_storage.resolve_wrong_record(rec_id, retest_score=95.0)
    assert resolved is True

    # Check pending list again
    remaining = test_storage.get_pending_wrong_records("user2")
    assert len(remaining) == 1
    assert remaining[0].question_id == "Q2"


def test_leaderboard(test_storage: Storage):
    test_storage.record_quiz_result("alice", "Q1", "T1", "A", 90.0, True)
    test_storage.record_quiz_result("bob", "Q1", "T1", "A", 100.0, True)
    test_storage.record_quiz_result("charlie", "Q1", "T1", "A", 60.0, True)

    leaders = test_storage.get_leaderboard(limit=2)
    assert len(leaders) == 2
    assert leaders[0].user_id == "bob"
    assert leaders[1].user_id == "alice"


def test_json_backup_and_restore(test_storage: Storage, tmp_path: Path):
    test_storage.record_quiz_result("cxk", "Q-PA", "P/A机制", "great answer", 100.0, True)
    test_storage.record_quiz_result("cxk", "Q-FAIL", "STP失败", "bad answer", 20.0, False)

    backup_file = tmp_path / "backup_storage.json"
    test_storage.export_json(backup_file)
    assert backup_file.exists()

    # Create a fresh storage and import
    fresh_storage = Storage(db_path=tmp_path / "fresh.db")
    fresh_storage.import_json(backup_file)

    user = fresh_storage.get_or_create_user("cxk")
    assert user.total_score == 120.0
    assert user.total_quizzes == 2
    wrongs = fresh_storage.get_pending_wrong_records("cxk")
    assert len(wrongs) == 1
    assert wrongs[0].question_id == "Q-FAIL"
