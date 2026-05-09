"""Pytest fixtures for Home Assistant-backed tests."""

from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> Generator[None, None, None]:
    """Reuse pytest-homeassistant-custom-component harness + local ``custom_components/``."""
    _ = enable_custom_integrations
    yield
