"""Thin LAN client layered on protobuf + AES framing (forked semantics from PyRobovac).

See PROTO_USAGE.md for field-level mapping docs.
"""

from __future__ import annotations

import logging
import random
import socket
import struct
from typing import cast

from . import crypto
from . import LocalServerInfo_pb2 as pb2
from .commands import RobovacCommands, RobovacModes, build_robovac_command

_LOGGER = logging.getLogger(__name__)


class RobovacStatus:
    """Status reported by legacy RoboVac firmware (mirror of archived PyRobovac)."""

    __slots__ = (
        "find_me",
        "water_tank_status",
        "mode",
        "speed",
        "charger_status",
        "battery_capacity",
        "error_code",
        "stop",
    )

    def __init__(
        self,
        *,
        find_me,
        water_tank_status,
        mode,
        speed,
        charger_status,
        battery_capacity,
        error_code,
        stop,
    ) -> None:
        self.find_me = find_me
        self.water_tank_status = water_tank_status
        self.mode = mode
        self.speed = speed
        self.charger_status = charger_status
        self.battery_capacity = battery_capacity
        self.error_code = error_code
        self.stop = stop


class Robovac:
    """Talk to a LAN-exposed legacy RoboVac using the protobuf/AES handshake."""

    @staticmethod
    def _parse_local_server_message(decrypted_response: bytes) -> pb2.LocalServerMessage:
        length = cast(int, struct.unpack("<H", decrypted_response[0:2])[0])
        protobuf_segment = decrypted_response[2 : length + 2]
        message = pb2.LocalServerMessage()
        message.ParseFromString(protobuf_segment)
        return message

    def __init__(self, ip: str, local_code: str, port: int = 55556) -> None:
        self.ip = ip
        self.port = port
        self.local_code = local_code
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        """Establish a fresh TCP socket to the appliance."""

        self.disconnect()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.ip, self.port))

    def disconnect(self) -> None:
        """Attempt to disconnect from the appliance."""

        if self._sock is None:
            return
        try:
            self._sock.close()
        except OSError:
            pass
        self._sock = None

    def get_status_with_raw(self) -> tuple[RobovacStatus, bytes]:
        message = self._build_get_device_status_user_data_message()
        robovac_response = self._send_packet(message, expect_reply=True)
        if robovac_response is None:
            raise OSError("expected status payload")

        usr_data = robovac_response.c.usr_data or b""
        received_status_ints = list(usr_data)
        if len(received_status_ints) < 14:
            raise OSError(f"status usr_data too short ({len(usr_data)} bytes, need >= 14)")

        status = RobovacStatus(
            find_me=1 if received_status_ints[6] & 4 > 0 else 0,
            water_tank_status=1 if received_status_ints[6] & 2 > 0 else 0,
            mode=received_status_ints[1] & 255,
            speed=received_status_ints[8] & 255,
            charger_status=received_status_ints[11] & 255,
            battery_capacity=received_status_ints[10] & 255,
            error_code=received_status_ints[12] & 255,
            stop=received_status_ints[13] & 255,
        )
        return status, usr_data

    def get_status(self) -> RobovacStatus:
        return self.get_status_with_raw()[0]

    def start_auto_clean(self) -> None:
        payload = build_robovac_command(RobovacModes.WORK, RobovacCommands.AUTO_CLEAN)
        self._emit_command(payload)

    def start_spot_clean(self) -> None:
        payload = build_robovac_command(RobovacModes.WORK, RobovacCommands.SPOT_CLEAN)
        self._emit_command(payload)

    def start_edge_clean(self) -> None:
        payload = build_robovac_command(RobovacModes.WORK, RobovacCommands.EDGE_CLEAN)
        self._emit_command(payload)

    def stop(self) -> None:
        payload = build_robovac_command(RobovacModes.WORK, RobovacCommands.STOP_CLEAN)
        self._emit_command(payload)

    def go_home(self) -> None:
        payload = build_robovac_command(RobovacModes.WORK, RobovacCommands.GO_HOME)
        self._emit_command(payload)

    def start_find_me(self) -> None:
        payload = build_robovac_command(RobovacModes.FIND_ME, RobovacCommands.START_RING)
        self._emit_command(payload)

    def use_normal_speed(self) -> None:
        payload = build_robovac_command(RobovacModes.SET_SPEED, RobovacCommands.SLOW_SPEED)
        self._emit_command(payload)

    def use_max_speed(self) -> None:
        payload = build_robovac_command(RobovacModes.SET_SPEED, RobovacCommands.FAST_SPEED)
        self._emit_command(payload)

    def go_forward(self) -> None:
        payload = build_robovac_command(RobovacModes.GO_FORWARD, RobovacCommands.MOVE)
        self._emit_command(payload)

    def go_backward(self) -> None:
        payload = build_robovac_command(RobovacModes.GO_BACKWARD, RobovacCommands.MOVE)
        self._emit_command(payload)

    def go_left(self) -> None:
        payload = build_robovac_command(RobovacModes.GO_LEFT, RobovacCommands.MOVE)
        self._emit_command(payload)

    def go_right(self) -> None:
        payload = build_robovac_command(RobovacModes.GO_RIGHT, RobovacCommands.MOVE)
        self._emit_command(payload)

    def _emit_command(self, command_payload: bytes) -> None:
        message = self._build_command_user_data_message(command_payload)
        self._send_packet(message, expect_reply=False)

    def _build_command_user_data_message(self, command_payload: bytes) -> pb2.LocalServerMessage:
        magic_number = self._get_magic_number()
        msg = pb2.LocalServerMessage()
        msg.magic_num = magic_number
        msg.localcode = self.local_code
        msg.c.type = 0  # sendUsrDataToDev
        msg.c.usr_data = command_payload
        return msg

    def _build_get_device_status_user_data_message(self) -> pb2.LocalServerMessage:
        magic_number = self._get_magic_number()
        msg = pb2.LocalServerMessage()
        msg.localcode = self.local_code
        msg.magic_num = magic_number
        msg.c.type = 1  # getDevStatusData
        return msg

    def _get_magic_number(self) -> int:
        ping = pb2.LocalServerMessage()
        ping.localcode = self.local_code
        ping.magic_num = random.randrange(3_000_000)

        ping.a.type = 0  # PingPacketType.PING_REQUEST

        pong = self._send_packet(ping, expect_reply=True)
        if pong is None:
            raise OSError("expected ping response")

        next_magic = pong.magic_num + 1
        return cast(int, next_magic)

    def _send_packet(self, packet: pb2.LocalServerMessage, *, expect_reply: bool) -> pb2.LocalServerMessage | None:
        if self._sock is None:
            raise OSError("socket not connected")

        raw_payload = packet.SerializeToString()
        encrypted = crypto.encrypt(raw_payload)

        try:
            self._sock.sendall(encrypted)
        except OSError:
            _LOGGER.exception("send failed — reconnect attempt")
            self.disconnect()
            self.connect()
            if self._sock is None:
                raise
            self._sock.sendall(encrypted)

        if not expect_reply:
            return None

        response_blob = self._sock.recv(1024)
        decrypted_response = crypto.decrypt(response_blob)
        return Robovac._parse_local_server_message(decrypted_response)
