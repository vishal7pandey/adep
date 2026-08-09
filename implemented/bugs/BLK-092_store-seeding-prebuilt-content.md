---
id: BLK-092
type: bug
title: "Backend: API stores return empty lists — no prebuilt skills/templates/definitions seeded"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: M
depends-on: [BLK-088]
tags: [backend, bug, seeding, store, stabilization]
---

## Bug

The `DefinitionStore` reads from `.adep/{entity_type}/*.json` files.
On a fresh install, these directories are empty — `list_skills()`,
`list_templates()`, and `list_definitions()` all return `[]`.

The frontend falls back to `MOCK_SKILLS` and `MOCK_TEMPLATES` when
the API returns empty, which masks the problem. But:

1. The wizard shows only 1 mock skill and 1 mock template
2. No prebuilt agent definitions exist
3. Starting a run with any definition fails because the store is empty

## Fix

Add a **seeding mechanism** that populates the store on first run:

```python
def seed_store(store: DefinitionStore) -> None:
    """Seed the store with prebuilt skills, templates, and definitions."""
    # Skills
    from src.skills.invoice import InvoiceSkill
    from src.skills.trade_finance import TradeFinanceSkill
    from src.skills.bill_of_quantities import BillOfQuantitiesSkill
    from src.skills.utility_bill import UtilityBillSkill

    for skill_id, skill in [
        ("sk-invoice-basic", InvoiceSkill),
        ("sk-trade-finance", TradeFinanceSkill),
        ("sk-boq", BillOfQuantitiesSkill),
        ("sk-utility-bill", UtilityBillSkill),
    ]:
        if not store.exists("skills", skill_id):
            store.create_skill(skill_id, {
                "id": skill_id,
                "name": skill.name,
                "description": skill.system_prompt[:200],
                "tools": list(skill.tool_preferences.values()),
                "semantic_checks_enabled": False,
            })

    # Templates — serialize field schemas
    # Definitions — wire skill + template + default config
```

Call `seed_store(get_store())` in `create_app()` or on first boot.

## Acceptance Criteria

- [ ] Fresh install has 4 skills, 4 templates, and at least 1
      prebuilt definition in the store
- [ ] `GET /skills` returns 4 skills without frontend mock fallback
- [ ] `GET /templates` returns 4 templates without frontend mock fallback
- [ ] `GET /definitions` returns at least 1 prebuilt definition
- [ ] A run can be started with a prebuilt definition without errors
