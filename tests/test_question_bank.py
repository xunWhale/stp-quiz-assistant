"""Tests for QuestionBank and question loading."""

import json
from pathlib import Path
import tempfile
import pytest

from stp_quiz.models import Category, QuestionType
from stp_quiz.question_bank import QuestionBank, DEFAULT_QUESTIONS


def test_question_bank_defaults():
    qb = QuestionBank()
    assert qb.count() == len(DEFAULT_QUESTIONS)
    assert qb.count() >= 8

    # Ensure required question types and categories exist
    all_qs = qb.list_all()
    categories = {q.category for q in all_qs}
    assert Category.STP_ELECTION in categories
    assert Category.PORT_ROLES_STATES in categories
    assert Category.RSTP_CONVERGENCE_PA in categories
    assert Category.MSTP_INSTANCE in categories
    assert Category.COMPREHENSIVE in categories

    qtypes = {q.qtype for q in all_qs}
    assert QuestionType.CHOICE in qtypes
    assert QuestionType.MULTI_CHOICE in qtypes
    assert QuestionType.ESSAY in qtypes


def test_filter_and_pick_random():
    qb = QuestionBank()

    # Filter by category
    rstp_qs = qb.filter(category=Category.RSTP_CONVERGENCE_PA)
    assert len(rstp_qs) >= 2
    for q in rstp_qs:
        assert q.category == Category.RSTP_CONVERGENCE_PA

    # Filter by type
    essay_qs = qb.filter(qtype=QuestionType.ESSAY)
    assert len(essay_qs) >= 3

    # Pick random
    picked = qb.pick_random(category=Category.STP_ELECTION)
    assert picked is not None
    assert picked.category == Category.STP_ELECTION

    # Exclude IDs
    all_elec_ids = [q.id for q in qb.filter(category=Category.STP_ELECTION)]
    assert qb.pick_random(category=Category.STP_ELECTION, exclude_ids=all_elec_ids) is None


def test_export_and_import_json(tmp_path: Path):
    qb = QuestionBank()
    export_file = tmp_path / "questions_test.json"

    qb.export_json(export_file)
    assert export_file.exists()

    with open(export_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == qb.count()

    # Create empty bank and import
    new_qb = QuestionBank(questions=[])
    assert new_qb.count() == 0
    imported = new_qb.import_json(export_file)
    assert imported == qb.count()
    assert new_qb.count() == qb.count()

    q_pa = new_qb.get("RSTP-PA-01")
    assert q_pa is not None
    assert q_pa.title.startswith("RSTP Proposal/Agreement")
