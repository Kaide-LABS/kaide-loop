"""The dispatch controller. Implements CUSTOMIZATION_PHASE_3_SPEC.md.

Names which of the three already-generated subagents (`loopr-step10`, `loopr-step11`,
`loopr-step12`) runs next, deterministically, from a small finite state space. Nothing in this
package calls an LLM, a judge, or a subprocess -- see `controller.py`'s module docstring for the
hard-boundary rationale.
"""

from __future__ import annotations
