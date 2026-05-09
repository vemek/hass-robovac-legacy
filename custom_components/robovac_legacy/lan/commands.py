"""Local RoboVac command bytes (MCU OTA framing) — vendored semantics from PyRobovac."""

from __future__ import annotations

from enum import IntEnum


class RobovacModes(IntEnum):
    WORK = 0xE1
    SET_SPEED = 0xE8
    FIND_ME = 0xEC
    GO_FORWARD = 0xE2
    GO_LEFT = 0xE4
    GO_RIGHT = 0xE5
    GO_BACKWARD = 0xE3


class RobovacCommands(IntEnum):
    AUTO_CLEAN = 0x02
    SINGLE_ROOM_CLEAN = 0x05
    SPOT_CLEAN = 0x01
    EDGE_CLEAN = 0x04
    STOP_CLEAN = 0x00
    GO_HOME = 0x03

    SLOW_SPEED = 0x00
    FAST_SPEED = 0x01

    START_RING = 0x01
    STOP_RING = 0x00

    MOVE = 0x01


def build_robovac_command(mode: RobovacModes, command: RobovacCommands) -> bytes:
    """Pack the MCU OTA preamble used by LAN protobuf commands."""

    mcu_ota_header_0xa5 = 0xA5
    cmd_data = mode.value + command.value

    return bytes([mcu_ota_header_0xa5, mode.value, command.value, cmd_data, 0xFA])
