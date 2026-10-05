"""Skill loader for the new engine (ADE-34): SKILL.md + schema.json as data, zero Python per skill.

Progressive disclosure: list_skills() is cheap (metadata only, for the skill-discovery tool),
load_skill() returns the full Skill (hints, schema, invariants) only when actually needed.

probe_order is parsed and kept on the Skill, but Skill.to_prompt_block() never renders it: skills
are knowledge for the agent to reason over, not a script to follow (ADE-12's explicit rule,
carried over from the ade2 prototype this design is ported from).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


@dataclass
class Skill:
    id: str
    name: str
    description: str
    hints: str
    schema: dict | None = None
    modality: str = "extraction"
    probe_order: list[dict] = field(default_factory=list)
    invariants: list[dict] = field(default_factory=list)
    ruleset: list[dict] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Render this skill as a knowledge block for the agent's prompt.

        Deliberately omits probe_order: the agent plans its own approach based on this
        knowledge and what it observes in the document, rather than following a script.
        """
        parts = [f"## Skill: {self.name}"]
        if self.description:
            parts.append(f"**Description**: {self.description}")
        if self.modality and self.modality != "extraction":
            parts.append(f"**Modality**: {self.modality}")
        if self.hints:
            parts.append(f"### Domain Knowledge\n{self.hints}")
        if self.invariants:
            lines = ["### Invariants (output must satisfy these)"]
            for inv in self.invariants:
                if isinstance(inv, dict):
                    desc = inv.get("description", "")
                    action = inv.get("verification_action", "")
                    line = f"- **{inv.get('name', 'unnamed')}**: {desc}"
                    if action:
                        line += f" (verify: {action})"
                    lines.append(line)
                elif isinstance(inv, str):
                    lines.append(f"- {inv}")
            parts.append("\n".join(lines))
        if self.ruleset:
            lines = ["### Design Rules (check against these)"]
            for rule in self.ruleset:
                if isinstance(rule, dict):
                    lines.append(
                        f"- **{rule.get('id', 'unnamed')}** [{rule.get('severity', 'MEDIUM')}]: "
                        f"{rule.get('description', '')}"
                    )
                elif isinstance(rule, str):
                    lines.append(f"- {rule}")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "modality": self.modality,
            "hints": self.hints,
            "schema": self.schema,
            "probe_order": self.probe_order,
            "invariants": self.invariants,
            "ruleset": self.ruleset,
        }


def _parse_frontmatter(md: str) -> tuple[dict, str]:
    """Split a SKILL.md into (frontmatter dict, body). No frontmatter -> ({}, md unchanged)."""
    if md.startswith("\ufeff"):
        md = md[1:]
    if not md.startswith("---"):
        return {}, md
    end = md.find("---", 3)
    if end == -1:
        return {}, md
    block = md[3:end].strip()
    body = md[end + 3 :].strip()

    import yaml

    data = yaml.safe_load(block) or {}
    return data, body


def list_skills() -> list[dict]:
    """Return every available skill's cheap metadata (for list_skills tool + API).

    Does not read schema.json or the markdown body — that's load_skill's job. Returns [] if
    SKILLS_DIR doesn't exist (no skills ported yet is a valid state, not an error).
    """
    skills: list[dict] = []
    if not SKILLS_DIR.exists():
        return skills
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        frontmatter, _ = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        skills.append(
            {
                "id": d.name,
                "name": frontmatter.get("name", d.name),
                "description": frontmatter.get("description", ""),
                "modality": frontmatter.get("modality", "extraction"),
                "category": frontmatter.get("category", "general"),
                "visual_cues": frontmatter.get("visual_cues", []),
                "document_aliases": frontmatter.get("document_aliases", []),
            }
        )
    return skills


def load_skill(skill_id: str) -> Skill | None:
    """Load one skill's full knowledge (hints, schema, invariants) by id.

    A malformed schema.json degrades to schema=None with a logged warning rather than raising:
    one bad skill must not take down the loader for every other skill.
    """
    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.is_dir():
        logger.debug("Skill not found: %s (no directory)", skill_id)
        return None
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        logger.debug("Skill not found: %s (no SKILL.md)", skill_id)
        return None

    frontmatter, body = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))

    schema: dict | None = None
    schema_file = skill_dir / "schema.json"
    if schema_file.exists():
        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse schema.json for skill '%s': %s", skill_id, exc)
            schema = None

    return Skill(
        id=skill_id,
        name=frontmatter.get("name", skill_id),
        description=frontmatter.get("description", ""),
        hints=body,
        schema=schema,
        modality=frontmatter.get("modality", "extraction"),
        probe_order=frontmatter.get("probe_order", []),
        invariants=frontmatter.get("invariants", []),
        ruleset=frontmatter.get("ruleset", []),
    )
