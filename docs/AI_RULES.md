# AI ENGINEERING RULES

These rules apply to every contributor.

Including:

- ChatGPT
- Claude
- Human Developers

---

# Architecture

Never duplicate business logic.

One calculation should exist in only one module.

Every module must have one responsibility.

---

# Analytics

Analytics modules never:

- Download data
- Save reports
- Display dashboards

Analytics modules only analyze data.

---

# Reports

Reports never calculate indicators.

Reports assemble existing analytical output.

---

# Collectors

Collectors only:

- Download
- Validate
- Normalize
- Store

Collectors never generate signals.

---

# Database

Use one database layer.

Never scatter SQL throughout the project.

---

# Interfaces

Every major analytics module exposes one public function.

Example

get_market_brain()

get_sector_strength()

get_market_levels()

Return structured objects.

Avoid returning formatted text.

---

# Code Quality

Prefer readable code.

Avoid clever shortcuts.

Prefer explicit names.

Keep functions short.

Keep modules independent.

---

# Documentation

Every new major module must be documented.

Architectural decisions belong in DECISIONS.md.

---

# Testing

Every logical milestone should be tested.

Never merge untested code.

---

# Development Philosophy

Collect Once.

Analyze Once.

Learn Forever.