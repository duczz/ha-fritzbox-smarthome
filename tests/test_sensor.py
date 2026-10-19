"""Tests for the power meter sensor values."""

from types import SimpleNamespace

import pytest

from custom_components.fritzbox.sensor import (
    SENSOR_TYPES,
    value_current,
    value_power,
    value_total_energy,
    value_voltage,
)


@pytest.mark.parametrize(
    ("func", "attribute", "raw", "expected"),
    [
        (value_power, "power", 12345, 12.345),
        (value_voltage, "voltage", 230123, 230.12),
        (value_current, "current", 1234, 1.234),
        (value_total_energy, "energy", 5000, 5.0),
        (value_power, "power", 0, 0.0),
        (value_total_energy, "energy", 0, 0.0),
    ],
)
def test_power_meter_values(func, attribute: str, raw: int, expected: float) -> None:
    """Reported values are converted; a real 0 stays 0."""
    assert func(SimpleNamespace(**{attribute: raw})) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("func", "attribute"),
    [
        (value_power, "power"),
        (value_voltage, "voltage"),
        (value_current, "current"),
        (value_total_energy, "energy"),
    ],
)
def test_power_meter_values_missing(func, attribute: str) -> None:
    """A missing value is unknown, not 0."""
    assert func(SimpleNamespace(**{attribute: None})) is None


@pytest.mark.parametrize(
    ("key", "attribute", "raw", "expected"),
    [
        ("power_consumption", "power", 12345, 12.345),
        ("voltage", "voltage", 230123, 230.12),
        ("electric_current", "current", 1234, 1.234),
        ("total_energy", "energy", 5000, 5.0),
        ("power_consumption", "power", 0, 0.0),
        ("power_consumption", "power", None, None),
        ("voltage", "voltage", None, None),
        ("electric_current", "current", None, None),
        ("total_energy", "energy", None, None),
    ],
)
def test_sensor_descriptions_use_the_values(
    key: str, attribute: str, raw: int | None, expected: float | None
) -> None:
    """The sensor descriptions are wired to the value functions."""
    description = next(desc for desc in SENSOR_TYPES if desc.key == key)
    value = description.native_value(SimpleNamespace(**{attribute: raw}))
    if expected is None:
        assert value is None
    else:
        assert value == pytest.approx(expected)
