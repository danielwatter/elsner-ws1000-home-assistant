from __future__ import annotations
import socket
import time
from dataclasses import dataclass

from .const import (
    CONFIG_REQUEST, INIT_REPLY, PORT, REQUEST_2, WEATHER_REQUEST, WS1000_PREFIX
)

CONNECT_TIMEOUT = 5.0
SOCKET_TIMEOUT = 2.0


@dataclass(frozen=True)
class WS1000Drive:
    object_id: int
    name: str
    kind: str


@dataclass(frozen=True)
class WS1000Group:
    object_id: int
    name: str


class WS1000Error(Exception):
    pass


class WS1000Client:
    def __init__(self, host: str) -> None:
        self.host = host

    def _recv_exact(self, sock: socket.socket, count: int) -> bytes:
        data = b""
        while len(data) < count:
            chunk = sock.recv(count - len(data))
            if not chunk:
                raise WS1000Error("WS1000 closed the connection")
            data += chunk
        return data

    def _recv_frame(self, sock: socket.socket) -> bytes:
        header = self._recv_exact(sock, 2)
        length = int.from_bytes(header, "big")
        return header + self._recv_exact(sock, length)

    def _connect(self) -> socket.socket:
        sock = socket.create_connection((self.host, PORT), timeout=CONNECT_TIMEOUT)
        sock.settimeout(SOCKET_TIMEOUT)
        self._recv_frame(sock)
        sock.sendall(INIT_REPLY)
        self._recv_frame(sock)
        sock.sendall(REQUEST_2)
        self._recv_frame(sock)
        return sock

    @staticmethod
    def _close(sock: socket.socket | None) -> None:
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

    @staticmethod
    def _outer(inner: bytes) -> bytes:
        payload = WS1000_PREFIX + inner
        return len(payload).to_bytes(2, "big") + payload

    def test_connection(self) -> None:
        sock = None
        try:
            sock = self._connect()
        finally:
            self._close(sock)

    def _read_config_frames(self) -> list[bytes]:
        """Read the complete WS1000 configuration frame stream."""
        sock = None
        frames: list[bytes] = []
        try:
            sock = self._connect()
            sock.sendall(CONFIG_REQUEST)
            for _ in range(500):
                try:
                    frame = self._recv_frame(sock)
                except (socket.timeout, WS1000Error):
                    break
                frames.append(frame)
        finally:
            self._close(sock)
        return frames

    @staticmethod
    def _decode_config_name(frame: bytes) -> str:
        if len(frame) < 570:
            return ""
        name_bytes = frame[569:].split(b"\x00", 1)[0]
        return name_bytes.decode("utf-8", errors="replace").strip()

    @staticmethod
    def _decode_drive_kind(frame: bytes) -> str:
        signature = frame[98:102]
        if signature == bytes.fromhex("00 01 00 02"):
            return "awning"
        if signature == bytes.fromhex("00 00 00 01"):
            return "blind"
        return "window"

    def discover_topology(self) -> tuple[list[WS1000Drive], list[WS1000Group]]:
        """Read config once and return physical actuators plus user groups."""
        frames = self._read_config_frames()

        drives: dict[int, WS1000Drive] = {}
        groups: dict[int, WS1000Group] = {}

        for frame in frames:
            if len(frame) < 570:
                continue

            oid = int.from_bytes(frame[19:21], "big")
            name = self._decode_config_name(frame)
            if not name:
                continue

            if 100 <= oid <= 107:
                drives[oid] = WS1000Drive(
                    oid,
                    name,
                    self._decode_drive_kind(frame),
                )
                continue

            # The WS1000 UI exposes 20 user group slots. On the wire these
            # are object IDs 0..19. Internal alarm/security objects (70..76)
            # are intentionally excluded.
            if 0 <= oid < 20:
                groups[oid] = WS1000Group(oid, name)

        if not drives:
            raise WS1000Error("No physical drives found in WS1000 configuration")

        return (
            sorted(drives.values(), key=lambda drive: drive.object_id),
            sorted(groups.values(), key=lambda group: group.object_id),
        )

    def _status_request(self, object_id: int) -> bytes:
        payload = bytes([
            0x00, 0x07, 0, 0, 0, 0, 0, 0, 0x05, 0x00,
            0, 0, 0, 0, 0, 0, 0x07,
            (object_id >> 8) & 0xFF, object_id & 0xFF,
            0x08, 0x01, 0x15, 0x00, 0x63,
        ])
        return len(payload).to_bytes(2, "big") + payload

    @staticmethod
    def _pos(value: int) -> int | None:
        if value in (0xFE, 0xFF):
            return None
        return value if 0 <= value <= 100 else None

    def read_status(self, object_id: int) -> dict:
        sock = None
        try:
            sock = self._connect()
            sock.sendall(self._status_request(object_id))
            for _ in range(8):
                frame = self._recv_frame(sock)
                if (
                    len(frame) >= 110
                    and frame[20] == (object_id & 0xFF)
                    and frame[21:24] == bytes.fromhex("09 01 15")
                ):
                    mode_raw = frame[25]
                    lock_raw = frame[58]
                    return {
                        "mode": "manual" if mode_raw == 0 else "auto" if mode_raw == 2 else "unknown",
                        "autolock": lock_raw == 2,
                        "position": self._pos(frame[81]),
                        "tilt": self._pos(frame[82]),
                        "target_position": self._pos(frame[108]),
                        "target_tilt": self._pos(frame[109]),
                        "moving": frame[81] == 0xFE,
                        "raw_status": frame[107],

                        # GUI_DF state values confirmed by Elsner:
                        #   0 = DISABLED
                        #   1 = VISIBLE
                        #   2 = HIGHLIGHTED
                        #   3 = ALARM
                        #
                        # Alarms are therefore active only for value 3.
                        "rain_alarm": frame[26] == 3,
                        "wind_alarm": frame[27] == 3,
                        "frost_alarm": frame[28] == 3,
                        "rain_alarm_raw": frame[26],
                        "wind_alarm_raw": frame[27],
                        "frost_alarm_raw": frame[28],
                        "gui_df": {
                            "automatic_mode": frame[25],
                            "rain_alarm": frame[26],
                            "wind_alarm": frame[27],
                            "frost_alarm": frame[28],
                            "smoke_alarm": frame[29],
                            "motion_alarm": frame[30],
                            "automatic_delay": frame[31],
                            "wind_direction": frame[32],
                            "wind_gap": frame[33],
                            "air_condition": frame[34],
                            "fresh_air": frame[35],
                            "outdoor_temp": frame[36],
                            "indoor_temp": frame[37],
                            "indoor_co2": frame[38],
                            "indoor_rh": frame[39],
                            "opening_time": frame[40],
                            "keep_close_time": frame[41],
                            "sun": frame[42],
                            "cloud": frame[43],
                            "sun_cloud_wait": frame[44],
                            "night": frame[45],
                            "solar_position": frame[46],
                            "driving_limit": frame[47],
                            "night_cooling": frame[48],
                            "safety": frame[49],
                            "sensor_error": frame[50],
                            "clock_timer": frame[51],
                            "outdoor_temp_block_hot": frame[52],
                            "outdoor_temp_block_cold": frame[53],
                            "indoor_temp_block_cold": frame[54],
                            "recirculation_heat_gain": frame[55],
                            "recirculation_condensation_reduction": frame[56],
                            "emergency_mode": frame[57],
                            "automatic_lock": frame[58],
                            "actuator_lock_info": frame[59],
                            "air_quality_block": frame[60],
                            "hcl_start_stop": frame[61],
                            "fancoil_auto": frame[62],
                            "reference_run": frame[63],
                        },
                    }
        finally:
            self._close(sock)
        raise WS1000Error(f"No status response for object {object_id}")


    @staticmethod
    def _u16le(frame: bytes, pos: int) -> int:
        return int.from_bytes(frame[pos:pos+2], "little", signed=False)

    @staticmethod
    def _u24be(frame: bytes, pos: int) -> int:
        return (frame[pos] << 16) | (frame[pos+1] << 8) | frame[pos+2]

    def read_weather(self) -> dict:
        sock = None
        try:
            sock = self._connect()
            sock.sendall(WEATHER_REQUEST)
            for _ in range(8):
                frame = self._recv_frame(sock)
                if len(frame) >= 202 and frame[21:24] == bytes.fromhex("09 01 16"):
                    flags = self._u16le(frame, 200)
                    return {
                        "inside_temperature": int.from_bytes(frame[28:30], "big", signed=True) / 10.0,
                        "inside_humidity": self._u16le(frame, 32) / 10.0,
                        "outside_temperature": int.from_bytes(frame[137:139], "big", signed=True) / 10.0,
                        "illuminance": self._u24be(frame, 141),
                        "wind_speed_ms": frame[163] / 10.0,
                        "wind_speed_kmh": (frame[163] / 10.0) * 3.6,
                        "rain": bool(frame[146]),
                        "flags": flags,
                    }
        finally:
            self._close(sock)
        raise WS1000Error("No weather response")

    def _drive_frame(self, object_id: int, command: str) -> bytes:
        inner = bytes([
            0x0B, (object_id >> 8) & 0xFF, object_id & 0xFF,
            0x06, 0x01, 0x14, ord(command), 0, 0, 0, 0, 0x63,
        ])
        return self._outer(inner)

    def _sequence(self, object_id: int, commands: list[str], delays: list[float]) -> None:
        sock = None
        try:
            sock = self._connect()
            for index, command in enumerate(commands):
                sock.sendall(self._drive_frame(object_id, command))
                if index < len(delays):
                    time.sleep(delays[index])
        finally:
            self._close(sock)

    def _position_frame(self, object_id: int, position: int, tilt: int = 0) -> bytes:
        """Direct WS1000 position command.

        Inner telegram:
          0B <obj_hi> <obj_lo> 06 01 14 42 <position> <tilt> 00 00 63

        0x42 = ASCII 'B'
        position / tilt = 0..100 percent
        """
        position = max(0, min(100, int(position)))
        tilt = max(0, min(100, int(tilt)))

        inner = bytes([
            0x0B,
            (object_id >> 8) & 0xFF,
            object_id & 0xFF,
            0x06, 0x01, 0x14,
            0x42,
            position,
            tilt,
            0x00, 0x00,
            0x63,
        ])
        return self._outer(inner)

    def set_position(self, object_id: int, position: int, tilt: int = 0) -> None:
        """Set travel and slat position with the confirmed B command."""
        sock = None
        try:
            sock = self._connect()
            sock.sendall(self._position_frame(object_id, position, tilt))
            time.sleep(0.2)
        finally:
            self._close(sock)

    def stop(self, object_id: int) -> None:
        """Direction-aware STOP using target versus actual position.

        Correct mapping:
          status["position"]        = frame[81]  = SFB actual position
          status["target_position"] = frame[108] = SH target position

        Therefore:
          SH target > SFB actual -> moving DOWN -> short UP stops
          SH target < SFB actual -> moving UP   -> short DOWN stops
        """
        try:
            status = self.read_status(object_id)

            actual = status.get("position")
            target = status.get("target_position")

            if actual is not None and target is not None:
                if target > actual:
                    self._sequence(object_id, ["U", "u"], [0.05])
                    return

                if target < actual:
                    self._sequence(object_id, ["D", "d"], [0.05])
                    return
        except Exception:
            pass

        # Keep the already proven fallback if direction cannot be determined.
        self._sequence(
            object_id,
            ["U", "u", "D", "d"],
            [0.10, 0.05, 0.10],
        )

    def _short_up(self, object_id: int) -> None:
        self._sequence(object_id, ["U", "u"], [0.20])

    def _short_down(self, object_id: int) -> None:
        self._sequence(object_id, ["D", "d"], [0.20])

    def _full_up(self, object_id: int) -> None:
        self._sequence(object_id, ["U", "P", "p"], [0.25, 1.0])

    def _full_down(self, object_id: int) -> None:
        self._sequence(object_id, ["D", "N", "n"], [0.25, 1.0])

    def short_up(self, object_id: int) -> None:
        """Short UP impulse for a physical actuator."""
        self._short_up(object_id)

    def short_down(self, object_id: int) -> None:
        """Short DOWN impulse for a physical actuator."""
        self._short_down(object_id)

    def full_up(self, object_id: int) -> None:
        """Full UP/retract for a physical actuator."""
        self._full_up(object_id)

    def full_down(self, object_id: int) -> None:
        """Full DOWN/extend for a physical actuator."""
        self._full_down(object_id)

    def group_short_up(self, group_id: int) -> None:
        """Short UP impulse for a WS1000 group."""
        self._short_up(group_id)

    def group_short_down(self, group_id: int) -> None:
        """Short DOWN impulse for a WS1000 group."""
        self._short_down(group_id)

    def group_full_up(self, group_id: int) -> None:
        """Full UP/retract for a WS1000 group."""
        self._full_up(group_id)

    def group_full_down(self, group_id: int) -> None:
        """Full DOWN/extend for a WS1000 group."""
        self._full_down(group_id)

    def group_stop_unknown_direction(self, group_id: int) -> None:
        """Fallback STOP when HA did not initiate the current group movement."""
        self._sequence(
            group_id,
            ["U", "u", "D", "d"],
            [0.10, 0.05, 0.10],
        )

    def _mode_frame(
        self,
        object_id: int,
        mode_code: int,
        lock_code: int,
        actuator_lock_code: int = 0,
    ) -> bytes:
        """Build Elsner DT_AUTOMATIC_FLAG_DATA (23 / 0x17).

        Flag order confirmed by Elsner:
          automatic_flag, frostflag, motor_test_flag, automatik_sperre,
          aktor_sperre, hcl_on_off, fan_auto, ext

        Flag values:
          0 = IGNORE_FLAG
          1 = SET_FLAG
          2 = RESET_FLAG
        """
        inner = bytes([
            0x0E, (object_id >> 8) & 0xFF, object_id & 0xFF,
            0x06, 0x01, 0x17,
            mode_code,          # automatic_flag
            0x00,               # frostflag
            0x00,               # motor_test_flag
            lock_code,          # automatik_sperre
            actuator_lock_code, # aktor_sperre
            0x00,               # hcl_on_off
            0x00,               # fan_auto
            0x00,               # ext
            0x63,
        ])
        return self._outer(inner)

    def _send_mode(
        self,
        object_id: int,
        mode_code: int = 0,
        lock_code: int = 0,
        actuator_lock_code: int = 0,
    ) -> None:
        sock = None
        try:
            sock = self._connect()
            sock.sendall(
                self._mode_frame(
                    object_id,
                    mode_code,
                    lock_code,
                    actuator_lock_code,
                )
            )
            time.sleep(0.2)
        finally:
            self._close(sock)

    def set_manual(self, object_id: int) -> None:
        self._send_mode(object_id, mode_code=0x02)

    def set_auto(self, object_id: int) -> None:
        self._send_mode(object_id, mode_code=0x01)

    def set_autolock(self, object_id: int, enabled: bool) -> None:
        self._send_mode(object_id, lock_code=0x01 if enabled else 0x02)

    def set_actuator_lock(self, object_id: int, enabled: bool) -> None:
        """Set or reset the actuator lock for one actuator slot."""
        self._send_mode(
            object_id,
            actuator_lock_code=0x01 if enabled else 0x02,
        )
