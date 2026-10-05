"""Tests for the new-engine skill loader (ADE-34): SKILL.md + schema.json as data.

Hermetic: every test builds its own skill directories under tmp_path and monkeypatches
SKILLS_DIR, so scenarios never share fixture state. No network, no LLM.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from src.engine import skills as engine_skills

VALID_SKILL_MD = """\
---
name: Valid Skill
description: A fixture skill used to test the loader.
modality: extraction
category: test
visual_cues:
  - a big red stamp
document_aliases:
  - test document
probe_order:
  - step: survey the page first
  - step: then crop the stamp
invariants:
  - name: non_empty_findings
    description: findings must be non-empty
ruleset:
  - id: RULE-1
    severity: HIGH
    description: every finding needs a bbox
---
## Domain Knowledge

This is the markdown body of the fixture skill.
"""

VALID_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {"type": "object"}}},
    "required": ["findings"],
}


def _write_skill(root: Path, skill_id: str, md: str, schema: dict | None = None) -> Path:
    skill_dir = root / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(md, encoding="utf-8")
    if schema is not None:
        (skill_dir / "schema.json").write_text(json.dumps(schema), encoding="utf-8")
    return skill_dir


def test_skills_dir_resolves_to_repo_root_slash_skills():
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert engine_skills.SKILLS_DIR == repo_root / "skills"


@pytest.fixture
def skills_root(tmp_path, monkeypatch):
    root = tmp_path / "skills"
    root.mkdir()
    monkeypatch.setattr(engine_skills, "SKILLS_DIR", root)
    return root


# --- AC1 ---------------------------------------------------------------------------------------


def test_list_skills_returns_metadata_for_valid_skills_only(skills_root):
    _write_skill(skills_root, "valid-skill", VALID_SKILL_MD, VALID_SCHEMA)
    _write_skill(
        skills_root,
        "valid-skill-2",
        "---\nname: Second\ndescription: d2\n---\nbody\n",
    )
    (skills_root / "not-a-skill-dir").mkdir()  # no SKILL.md inside

    result = engine_skills.list_skills()

    ids = {s["id"] for s in result}
    assert ids == {"valid-skill", "valid-skill-2"}
    one = next(s for s in result if s["id"] == "valid-skill")
    assert one["name"] == "Valid Skill"
    assert one["description"] == "A fixture skill used to test the loader."
    assert one["modality"] == "extraction"
    assert one["category"] == "test"
    assert one["visual_cues"] == ["a big red stamp"]
    assert one["document_aliases"] == ["test document"]


def test_list_skills_on_missing_or_empty_dir_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_skills, "SKILLS_DIR", tmp_path / "does-not-exist")
    assert engine_skills.list_skills() == []


# --- AC2 ---------------------------------------------------------------------------------------


def test_load_skill_returns_full_skill_or_none(skills_root):
    _write_skill(skills_root, "valid-skill", VALID_SKILL_MD, VALID_SCHEMA)

    skill = engine_skills.load_skill("valid-skill")
    assert skill is not None
    assert skill.id == "valid-skill"
    assert "markdown body" in skill.hints
    assert skill.schema == VALID_SCHEMA
    assert skill.probe_order == [
        {"step": "survey the page first"},
        {"step": "then crop the stamp"},
    ]

    assert engine_skills.load_skill("nonexistent-skill") is None


# --- AC3 ---------------------------------------------------------------------------------------


def test_load_skill_without_schema_json_has_none_schema(skills_root):
    _write_skill(skills_root, "no-schema-skill", VALID_SKILL_MD, schema=None)

    skill = engine_skills.load_skill("no-schema-skill")
    assert skill is not None
    assert skill.schema is None


# --- AC4 ---------------------------------------------------------------------------------------


def test_malformed_schema_json_logs_warning_and_degrades(skills_root, caplog):
    skill_dir = _write_skill(skills_root, "bad-schema-skill", VALID_SKILL_MD, schema=None)
    (skill_dir / "schema.json").write_text("{not valid json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="src.engine.skills"):
        skill = engine_skills.load_skill("bad-schema-skill")

    assert skill is not None
    assert skill.schema is None
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("bad-schema-skill" in r.getMessage() for r in warnings)


# --- AC5 ---------------------------------------------------------------------------------------


def test_to_prompt_block_omits_probe_order(skills_root):
    _write_skill(skills_root, "valid-skill", VALID_SKILL_MD, VALID_SCHEMA)
    skill = engine_skills.load_skill("valid-skill")

    block = skill.to_prompt_block()

    assert "non_empty_findings" in block
    assert "RULE-1" in block
    assert "survey the page first" not in block
    assert "then crop the stamp" not in block


# --- AC6 ---------------------------------------------------------------------------------------


def test_bom_and_non_bom_skill_md_parse_identically(skills_root):
    _write_skill(skills_root, "with-bom", "﻿" + VALID_SKILL_MD, VALID_SCHEMA)
    _write_skill(skills_root, "without-bom", VALID_SKILL_MD, VALID_SCHEMA)

    with_bom = engine_skills.load_skill("with-bom")
    without_bom = engine_skills.load_skill("without-bom")

    assert with_bom.name == without_bom.name == "Valid Skill"
    assert with_bom.hints == without_bom.hints
    assert with_bom.invariants == without_bom.invariants


def test_skill_md_with_no_frontmatter_loads_with_empty_metadata(skills_root):
    plain = "Just a plain markdown file with no frontmatter block at all.\n"
    _write_skill(skills_root, "plain-skill", plain)

    skill = engine_skills.load_skill("plain-skill")

    assert skill is not None
    assert skill.name == "plain-skill"  # falls back to the id
    assert skill.description == ""
    assert skill.hints == plain
    assert skill.invariants == []
