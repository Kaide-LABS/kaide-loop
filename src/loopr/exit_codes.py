"""The machine-readable exit-code contract. Implements PHASE_1_SPEC.md SS6.1.

Named constants, not literals -- and 40 (HALT) is terminal by design, never auto-retried. This is
the lesson carried directly from the abandoned Docker harness, which retried deterministic failures
because it could only distinguish 'clean status vs not' (loopr-MIGRATION.md section 7).
"""

from __future__ import annotations

OK = 0
JUDGE_REQUIRED = 10
GATE_REQUIRED = 20
QUESTION_REQUIRED = 30
HALT = 40
COMPLETE = 50
USAGE = 2
