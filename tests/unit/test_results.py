"""Unit tests for ``sunxue_gates.results``.

Covers the dataclass shapes and the ``merge_passed`` aggregator.
"""

from __future__ import annotations

from sunxue_gates.results import CheckResult, GateResult, merge_passed


def _check(name: str, passed: bool, msg: str = "") -> CheckResult:
    return CheckResult(name=name, passed=passed, message=msg)


class TestCheckResult:
    def test_frozen_immutable(self) -> None:
        c = _check("a", True)
        try:
            c.passed = False  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("CheckResult should be frozen")

    def test_default_detail_is_empty_dict(self) -> None:
        c = _check("a", True)
        assert c.detail == {}

    def test_detail_payload_round_trip(self) -> None:
        c = CheckResult(name="a", passed=False, message="x", detail={"k": 1, "n": [1, 2]})
        assert c.detail == {"k": 1, "n": [1, 2]}


class TestGateResult:
    def test_failure_count_zero_when_all_pass(self) -> None:
        gr = GateResult(
            name="g",
            passed=True,
            details=(_check("a", True), _check("b", True)),
            summary="PASS",
        )
        assert gr.failure_count == 0
        assert gr.passed is True

    def test_failure_count_when_some_fail(self) -> None:
        gr = GateResult(
            name="g",
            passed=False,
            details=(_check("a", True), _check("b", False), _check("c", False)),
            summary="FAIL",
        )
        assert gr.failure_count == 2

    def test_details_is_a_tuple(self) -> None:
        gr = GateResult(name="g", passed=True, details=(), summary="")
        assert isinstance(gr.details, tuple)


class TestMergePassed:
    def test_empty_is_true(self) -> None:
        assert merge_passed([]) is True

    def test_all_true(self) -> None:
        assert merge_passed([True, True, True]) is True

    def test_any_false_is_false(self) -> None:
        assert merge_passed([True, False, True]) is False
        assert merge_passed([False]) is False
