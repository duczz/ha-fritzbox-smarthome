"""Fixtures for the FRITZ!SmartHome tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of the custom integration in every test."""


@pytest.fixture
def fritz() -> Generator[MagicMock]:
    """Patch the Fritzhome client used by the config flow."""
    with patch("custom_components.fritzbox.config_flow.Fritzhome") as mock_class:
        mock_class.return_value.has_smarthome_capabilities.return_value = True
        yield mock_class.return_value


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Prevent the real setup of the integration after a flow finished."""
    with (
        patch(
            "custom_components.fritzbox.async_setup_entry", return_value=True
        ) as mock_setup,
        patch("custom_components.fritzbox.async_unload_entry", return_value=True),
    ):
        yield mock_setup
