# Contributing

Thanks for helping developers build options software that gets the maths and the plumbing right. Fixes, new skills, better
checklists and corrections are all welcome.

## Ways to help

- **Fix a fact.** Exchange rules, lot sizes, expiries, taxes and broker APIs change often. If a rule, limit
  or header is out of date, open a PR with a link to the official source.
- **Improve a skill.** Each skill is a folder in `plugins/options-desk/skills/`
  with a `SKILL.md` (YAML frontmatter `name` + `description`, then instructions).
- **Add a skill.** Same layout. Keep `SKILL.md` under 500 lines; put long
  reference material in a separate file linked from it.
- **Improve the scripts** in `options-pricing/scripts` and `options-strategies/scripts`.
  They must stay standard-library only and keep their `--self-test` passing.

## Before you open a PR

```bash
python tests/validate_repo.py
python plugins/options-desk/skills/options-pricing/scripts/options_calc.py --self-test
python plugins/options-desk/skills/options-strategies/scripts/options_strategy.py --self-test
```

Code samples must run as written and use sandbox or paper accounts only; never
real API keys, access tokens, webhook secrets or client IDs.

## Ground rules

- Accuracy over volume: cite official docs for platform facts.
- Regulatory content is engineering guidance, not legal or tax advice; cite the exchange, clearing house, regulator or broker's official documentation.
- Never include real API keys, account numbers or personal data.
