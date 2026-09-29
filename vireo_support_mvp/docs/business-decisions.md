# Business/data decisions to state in the submission

- Analysis window: 2025-01-01 inclusive to 2026-07-01 exclusive.
- Legacy resolution timestamps: shift from UTC to IST (+05:30) before handle-time calculations.
- `transfers` blank on legacy rows means unknown, not zero.
- Category is treated as an imperfect intake label. The AI classifier operates on customer message + agent closing note.
- `recommended_team` is deterministic from policy ownership, not model-generated.
- Tier 2 is not ranked against Tier 1 solely by ticket volume.
- Accuracy should be reported only against human-verified labels. Model agreement with existing tags is a separate diagnostic.
