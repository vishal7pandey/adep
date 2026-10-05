# Notes — ADE-29

- 2026-10-05: baselines before the change: frontend `pnpm test` 10 files / 104 tests pass; `pnpm lint` 66 problems
  (22 errors, 44 warnings); case-insensitive grep over the tree: 222 references in 25 text files plus 7 coincidental
  binary matches in `sample-data/`.
- 2026-10-05: spec AC1 wording amended after approval (clarification only, same intent): the grep excludes
  `sample-data/`, because 7 compressed JPG/PDF files contain the abbreviation-with-ampersand byte sequence by chance
  (not a mention; editing them would corrupt the demo set). Not behaviour-changing; mention at merge.
- 2026-10-05: decision, recorded in spec Assumptions: no read of the old localStorage key (the ticket's suggestion),
  because it would keep the employer string in the code and contradict AC1. Cost: one-time theme reset.
