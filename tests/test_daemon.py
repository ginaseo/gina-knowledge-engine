"""Tests for daemon — _parse_interval and RetryPolicy."""
import pytest

from processor.daemon import _parse_interval, RetryPolicy


# ------------------------------------------------------------------
# _parse_interval
# ------------------------------------------------------------------

def test_parse_interval_seconds():
    assert _parse_interval("30s") == 30


def test_parse_interval_minutes():
    assert _parse_interval("5m") == 300


def test_parse_interval_hours():
    assert _parse_interval("2h") == 7200


def test_parse_interval_days():
    assert _parse_interval("1d") == 86400


def test_parse_interval_keyword_hour():
    assert _parse_interval("hour") == 3600


def test_parse_interval_keyword_day():
    assert _parse_interval("day") == 86400


def test_parse_interval_keyword_sunday():
    assert _parse_interval("sunday") == 7 * 86400


def test_parse_interval_raw_int():
    assert _parse_interval("120") == 120


# ------------------------------------------------------------------
# RetryPolicy.wait_for
# ------------------------------------------------------------------

def test_retry_exponential_attempt0():
    p = RetryPolicy(count=3, delay=30, backoff="exponential")
    assert p.wait_for(0) == 30   # 30 * 2^0


def test_retry_exponential_attempt1():
    p = RetryPolicy(count=3, delay=30, backoff="exponential")
    assert p.wait_for(1) == 60   # 30 * 2^1


def test_retry_linear_attempt0():
    p = RetryPolicy(count=3, delay=10, backoff="linear")
    assert p.wait_for(0) == 10   # 10 * (0+1)


def test_retry_linear_attempt2():
    p = RetryPolicy(count=3, delay=10, backoff="linear")
    assert p.wait_for(2) == 30   # 10 * (2+1)


def test_retry_fixed_any_attempt():
    p = RetryPolicy(count=3, delay=15, backoff="fixed")
    assert p.wait_for(0) == 15.0
    assert p.wait_for(5) == 15.0
