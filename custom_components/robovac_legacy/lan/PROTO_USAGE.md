# LAN protobuf surfaces (inventory)

Upstream reference: archived **PyRobovac 0.0.9** wheels (`robovac/robovac.py`). This integration only uses **`LocalServerMessage`** fields routed through **`playload`** (proto2-oneof wired as fields `a`–`d`).

| Scenario | Payload | Fields set |
|---------|---------|-----------|
| Session bootstrap / magic number handshake | **`a`** (ping) | `magic_num`, `localcode`, `a.type=PING_REQUEST` (0). Response supplies next `magic_num`. |
| Command (clean, speed, joystick, locate) | **`c`** | `magic_num`, `localcode`, `c.type=sendUsrDataToDev` (0), `c.usr_data` holds 5‑byte MCU frame (`_build_robovac_command`). |
| Poll status (`getDevStatusData`) | **`c`** | `magic_num`, `localcode`, `c.type=getDevStatusData` (1), no `usr_data`. Response `usr_data` is parsed into ints for **`RobovacStatus`**. |

OTA (`b`) and device-info (`d`) arms exist on the descriptor but **`robovac_legacy` leaves them untouched**.

Golden wire samples (parity with archived PyRobovac, `SerializeToString`):

- **`USERDATA_CMD_HEX`**: `080912106162636465666768696a6b6c6d6e6f702a0908001205a5e102e3fa` — `magic_num=9`, localcode `abcdefghijklmnop`, `sendUsrDataToDev` + `usr_data=A5 E1 02 E3 FA` (AUTO_CLEAN frame body).
- **`PING_HEX`**: `08d7a1930112106162636465666768696a6b6c6d6e6f701a020800` — `magic_num=2_412_759`, ping `type=0`, same dummy local_code (`2412759 → varint hex d7a19301`).
