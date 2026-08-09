"""LLM call audit logging & trace integrity [BLK-084].

Every LLM call is logged with full context. Logs are tamper-evident
(chained hashes) and retained per policy.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30


@dataclass
class AuditLogEntry:
    """A single audit log entry for an LLM call [BLK-084].

    Attributes:
        timestamp: ISO 8601 timestamp.
        run_id: Run identifier.
        cycle: Cycle number within the run.
        node: Graph node that triggered the call.
        system_prompt_hash: SHA256 hash of system prompt.
        user_prompt: Full user prompt (PII redacted).
        llm_response: Full LLM response.
        input_tokens: Input token count.
        output_tokens: Output token count.
        cost_usd: Cost in USD.
        latency_ms: Call latency in milliseconds.
        validation_passed: Whether output validation passed.
        guardrail_actions: List of guardrail actions taken.
        prev_hash: Hash of the previous log entry (chain integrity).
        entry_hash: Hash of this entry (computed on save).
    """

    timestamp: str = ""
    run_id: str = ""
    cycle: int = 0
    node: str = ""
    system_prompt_hash: str = ""
    user_prompt: str = ""
    llm_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    validation_passed: bool = True
    guardrail_actions: list[str] = field(default_factory=list)
    prev_hash: str = ""
    entry_hash: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSONL persistence."""
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "cycle": self.cycle,
            "node": self.node,
            "system_prompt_hash": self.system_prompt_hash,
            "user_prompt": self.user_prompt,
            "llm_response": self.llm_response,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "validation_passed": self.validation_passed,
            "guardrail_actions": self.guardrail_actions,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }

    def compute_hash(self) -> str:
        """Compute SHA256 hash of this entry (excluding entry_hash field) [BLK-084]."""
        data = self.to_dict()
        data.pop("entry_hash", None)
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class GuardrailDecision:
    """A guardrail decision log entry [BLK-084].

    Attributes:
        timestamp: ISO 8601 timestamp.
        run_id: Run identifier.
        guardrail: Which guardrail fired.
        action: What was rejected/sanitized.
        corrective_action: What was done (retry, terminate, flag).
        details: Additional context.
    """

    timestamp: str = ""
    run_id: str = ""
    guardrail: str = ""
    action: str = ""
    corrective_action: str = ""
    details: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "guardrail": self.guardrail,
            "action": self.action,
            "corrective_action": self.corrective_action,
            "details": self.details,
        }


class AuditLogger:
    """Tamper-evident audit logger for LLM calls [BLK-084].

    Logs are stored as JSONL files in `.adep/runs/{run_id}/audit_log.jsonl`.
    Each entry includes a hash of the previous entry, forming a chain.
    Tampering with any entry breaks the chain.

    Attributes:
        run_id: Run identifier.
        log_path: Path to the JSONL log file.
        _last_hash: Hash of the last written entry (for chaining).
    """

    def __init__(self, run_id: str, base_dir: Path | None = None) -> None:
        self.run_id = run_id
        if base_dir is None:
            base_dir = Path(".adep")
        self.log_path = base_dir / "runs" / run_id / "audit_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Load the hash of the last entry from existing log."""
        if not self.log_path.exists():
            return ""
        last_hash = ""
        for line in self.log_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    entry = json.loads(line)
                    last_hash = entry.get("entry_hash", "")
                except json.JSONDecodeError:
                    pass
        return last_hash

    def log_llm_call(self, entry: AuditLogEntry) -> str:
        """Log an LLM call entry [BLK-084].

        Args:
            entry: The audit log entry to record.

        Returns:
            The computed entry hash.
        """
        entry.prev_hash = self._last_hash
        entry.entry_hash = entry.compute_hash()

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        self._last_hash = entry.entry_hash
        logger.debug("Audit log entry written for run %s, cycle %d [BLK-084]", self.run_id, entry.cycle)
        return entry.entry_hash

    def log_guardrail_decision(self, decision: GuardrailDecision) -> None:
        """Log a guardrail decision [BLK-084]."""
        decision_path = self.log_path.parent / "guardrail_decisions.jsonl"
        with decision_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision.to_dict()) + "\n")

    def verify_chain(self) -> tuple[bool, str]:
        """Verify the integrity of the log chain [BLK-084].

        Returns:
            Tuple of (is_valid, message). If invalid, message describes the break.
        """
        if not self.log_path.exists():
            return True, "No log file"

        entries: list[dict[str, Any]] = []
        for line in self.log_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    return False, f"Corrupted log line: {e}"

        prev_hash = ""
        for i, entry in enumerate(entries):
            if entry.get("prev_hash") != prev_hash:
                return False, f"Chain broken at entry {i}: prev_hash mismatch"
            # Recompute hash
            data = entry.copy()
            stored_hash = data.pop("entry_hash", "")
            content = json.dumps(data, sort_keys=True)
            computed_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if computed_hash != stored_hash:
                return False, f"Hash mismatch at entry {i}: tampering detected"
            prev_hash = stored_hash

        return True, f"Chain valid ({len(entries)} entries)"

    def export_json(self) -> str:
        """Export audit log as JSON array [BLK-084]."""
        if not self.log_path.exists():
            return "[]"
        entries = []
        for line in self.log_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                entries.append(json.loads(line))
        return json.dumps(entries, indent=2)

    def export_csv(self) -> str:
        """Export audit log as CSV [BLK-084]."""
        if not self.log_path.exists():
            return ""

        entries: list[dict[str, Any]] = []
        for line in self.log_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                entries.append(json.loads(line))

        if not entries:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "timestamp", "run_id", "cycle", "node",
            "system_prompt_hash", "input_tokens", "output_tokens",
            "cost_usd", "latency_ms", "validation_passed",
            "guardrail_actions", "entry_hash",
        ])
        writer.writeheader()
        for entry in entries:
            row = entry.copy()
            row["guardrail_actions"] = "; ".join(entry.get("guardrail_actions", []))
            # Skip user_prompt and llm_response in CSV (too large)
            writer.writerow({k: row.get(k, "") for k in writer.fieldnames})

        return output.getvalue()


def hash_prompt(prompt: str) -> str:
    """Compute SHA256 hash of a prompt [BLK-084].

    Args:
        prompt: The prompt text to hash.

    Returns:
        Hex digest of the SHA256 hash.
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
