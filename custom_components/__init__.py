"""Namespace hook so editable ``custom_components``, ``pytest``, and HA share one tree."""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
