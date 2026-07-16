"""Marks the suite as a package so the type gate can address it.

Without this file mypy resolves each test as a top-level module (`test_audit_parser`
rather than `tests.test_audit_parser`), and the `[mypy-tests.*]` override in
mypy.ini silently matches nothing: the suite would be held to the production
narrowing rules it is deliberately exempt from. Do not delete it without moving
that override.
"""
