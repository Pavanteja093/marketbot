# ARCHITECTURAL DECISIONS

---

## Decision 001

Date

24 July 2026

Decision

MarketBot is a Market Intelligence Platform.

Reason

The long-term objective is research and decision support rather than simple trading signals.

---

## Decision 002

Market Levels owns all support and resistance calculations.

Reason

Avoid duplicated calculations across analytics modules.

---

## Decision 003

Reports never calculate indicators.

Reason

Maintain separation between analytics and presentation.

---

## Decision 004

Every analytics module exposes one public interface.

Reason

Simplifies integration and testing.