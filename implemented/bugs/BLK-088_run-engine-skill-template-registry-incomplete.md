---
id: BLK-088
type: bug
title: "Backend: run_engine skill/template registry only has invoice — 3 existing skills unregistered"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, registry, run-engine, stabilization]
---

## Bug

`src/api/run_engine.py` lines 33-42 — the `_SKILL_REGISTRY` and
`_TEMPLATE_REGISTRY` only contain `invoice`. The 3 other implemented
skills (`trade_finance`, `bill_of_quantities`, `utility_bill`) are
**not registered**. Any run using those skills will fail with
`ValueError: Unknown skill`.

```python
# Current — only invoice
_SKILL_REGISTRY: dict[str, Skill] = {
    "invoice": InvoiceSkill,
    "sk-invoice-basic": InvoiceSkill,
}

_TEMPLATE_REGISTRY: dict[str, type[Template]] = {
    "invoice": InvoiceTemplate,
    "tmpl-invoice-standard": InvoiceTemplate,
}
```

## Fix

Register all 4 existing skills and templates:

```python
from src.skills.trade_finance import TradeFinanceSkill
from src.skills.bill_of_quantities import BillOfQuantitiesSkill
from src.skills.utility_bill import UtilityBillSkill
from src.templates.trade_finance import TradeFinanceTemplate
from src.templates.bill_of_quantities import BillOfQuantitiesTemplate
from src.templates.utility_bill import UtilityBillTemplate

_SKILL_REGISTRY: dict[str, Skill] = {
    "invoice": InvoiceSkill,
    "sk-invoice-basic": InvoiceSkill,
    "trade_finance": TradeFinanceSkill,
    "sk-trade-finance": TradeFinanceSkill,
    "bill_of_quantities": BillOfQuantitiesSkill,
    "sk-boq": BillOfQuantitiesSkill,
    "utility_bill": UtilityBillSkill,
    "sk-utility-bill": UtilityBillSkill,
}

_TEMPLATE_REGISTRY: dict[str, type[Template]] = {
    "invoice": InvoiceTemplate,
    "tmpl-invoice-standard": InvoiceTemplate,
    "trade_finance": TradeFinanceTemplate,
    "tmpl-trade-finance": TradeFinanceTemplate,
    "bill_of_quantities": BillOfQuantitiesTemplate,
    "tmpl-boq": BillOfQuantitiesTemplate,
    "utility_bill": UtilityBillTemplate,
    "tmpl-utility-bill": UtilityBillTemplate,
}
```

## Acceptance Criteria

- [ ] All 4 existing skills registered in `_SKILL_REGISTRY`
- [ ] All 4 existing templates registered in `_TEMPLATE_REGISTRY`
- [ ] Runs using `trade_finance`, `bill_of_quantities`, or
      `utility_bill` skill IDs no longer fail
- [ ] Unit test verifying all registry entries resolve
