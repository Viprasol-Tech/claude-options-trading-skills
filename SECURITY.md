# Security policy

## Reporting a vulnerability

Please report security problems privately through
[GitHub security advisories](https://github.com/Viprasol-Tech/claude-options-trading-skills/security/advisories/new)
or by email to [support@viprasol.com](mailto:support@viprasol.com). Do not open a public issue.
We aim to reply within 3 working days.

## Scope

- The bundled scripts (`options_calc.py`, `options_strategy.py`): they read
  command-line values and print results. They make no network calls and run
  no shell commands. A wrong price, Greek, breakeven or max loss is in scope.
- Skill instructions that could lead an assistant to weaken account safety:
  naked short options presented as defined risk, legging without protection,
  unbounded retries, or missing risk limits.

## Keep secrets out of chats

These skills never need your keys or funds. Never paste broker or exchange API keys,
access tokens, webhook secrets or TOTP seeds into an issue, pull request or
chat. Use synthetic data and sandbox keys. If a key has been
exposed, rotate it with your provider immediately.
