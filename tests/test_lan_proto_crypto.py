"""Vendored LAN stack: AES helpers + deterministic protobuf payloads."""

from __future__ import annotations

from custom_components.robovac_legacy.lan import crypto
from custom_components.robovac_legacy.lan import LocalServerInfo_pb2


def test_aes_decrypt_recovers_plaintext_exact_pad() -> None:
    plaintext = bytes(range(47))
    assert crypto.decrypt(crypto.encrypt(plaintext))[: len(plaintext)] == plaintext


def test_local_wire_golden_sequences() -> None:
    code = "abcdefghijklmnop"
    cmd = LocalServerInfo_pb2.LocalServerMessage()
    cmd.magic_num = 9
    cmd.localcode = code
    cmd.c.type = 0  # sendUsrDataToDev
    cmd.c.usr_data = bytes([0xA5, 0xE1, 0x02, 0xE3, 0xFA])
    assert (
        cmd.SerializeToString().hex()
        == "080912106162636465666768696a6b6c6d6e6f702a0908001205a5e102e3fa"
    ), "update PROTO_USAGE.md USERDATA golden if this shifts"

    ping = LocalServerInfo_pb2.LocalServerMessage()
    ping.localcode = code
    ping.magic_num = 2_412_759
    ping.a.type = 0  # PingPacketType.PING_REQUEST
    assert (
        ping.SerializeToString().hex()
        == "08d7a1930112106162636465666768696a6b6c6d6e6f701a020800"
    ), "update PROTO_USAGE.md PING golden if this shifts"


def test_build_robovac_command_matches_auto_clean_fixture() -> None:
    from custom_components.robovac_legacy.lan.commands import (
        RobovacCommands,
        RobovacModes,
        build_robovac_command,
    )

    assert build_robovac_command(RobovacModes.WORK, RobovacCommands.AUTO_CLEAN) == bytes(
        [0xA5, 0xE1, 0x02, 0xE3, 0xFA]
    )


def test_decrypt_sample_frame_roundtrips_through_parse_path() -> None:
    pb = LocalServerInfo_pb2.LocalServerMessage()
    pb.magic_num = 9
    pb.localcode = "abcdefghijklmnop"
    pb.c.type = 0
    pb.c.usr_data = bytes([0x01, 0x02])

    raw_plain = pb.SerializeToString()
    frame = crypto.encrypt(raw_plain)

    decrypted = crypto.decrypt(frame)
    decoded = decrypted[: len(raw_plain)]

    roundtrip = LocalServerInfo_pb2.LocalServerMessage.FromString(decoded)
    assert roundtrip.magic_num == 9


