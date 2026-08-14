---
id: BLK-175
type: idea
title: "Definition marketplace and vetted template library for reusable extraction recipes"
priority: medium
status: backlog
phase: 5
owner: unassigned
created: 2026-08-09T09:25:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-067, BLK-068, BLK-069]
tags: [platform, discovery, templates, agent-definitions, marketplace, reuse]
---

## Description

The project is already structured around definitions, skills, and templates as reusable bricks. As the platform grows, users need a way to discover proven patterns instead of creating each agent definition from scratch. This item proposes a marketplace-like gallery of vetted document extraction recipes: invoice templates, P&ID skill packs, contract parsing definitions, utility-bill extraction, and other reusable combinations.

This is not just a UI improvement. It is a platform product capability: a way to share, review, and adopt known-good extraction recipes across teams and document classes.

## Motivation

The vision explains that ADEP is a platform, not just a pipeline. A platform becomes more valuable when users can browse and reuse patterns that are known to work, rather than assembling every definition manually. This is especially important for industries with repeated document types: insurance claims, bills of materials, P&ID diagrams, purchase orders, utility bills, and trade-finance documents.

## Acceptance Criteria

- [ ] Users can browse a catalog of curated reusable agent definitions and templates
- [ ] Each entry includes document type, confidence profile, required tools, and key fields
- [ ] Definitions can be filtered by industry, document class, and complexity
- [ ] Users can preview or clone a definition into their workspace
- [ ] Curated entries include provenance and a recommended “safe to adopt” status
- [ ] Community or internal marketplace entries can be rated or reviewed

## Constraints

- Should not force a cloud-hosted SaaS model
- Needs trust and governance controls; not every third-party template should be adopted silently
- Marketplace entries should carry compatibility metadata for template version and tool environment

## Dependencies

- BLK-067 (AI template composer)
- BLK-068 (AI skill composer)
- BLK-069 (agent composer)
- registry and search improvements already underway

## Notes

- Aligns with the project’s “platform” thesis in `vision.md`
- Makes the project more usable for enterprise scaling and cross-team reuse
- Useful for reducing onboarding time for new document classes and support teams

## Implementation Log

- **2026-08-09T09:25 (mgmt)**: Proposed from product-platform review to close the gap between “reusable building blocks” and “discoverable production patterns.”
