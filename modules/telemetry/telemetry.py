"""
Telemetry gathering logic.
"""

import time

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================


class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> "tuple[True, Telemetry] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Telemetry object.
        """
        return True, cls(cls.__private_key, connection, local_logger)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"

        self.connection = connection
        self.logger = local_logger
        self.read_timeout = 1.0

    def run(
        self,
    ) -> "tuple[True, TelemetryData] | tuple[False, None]":
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        start = time.time()
        end = start + self.read_timeout
        position_msg = None
        attitude_msg = None

        while time.time() < end:
            remaining = end - time.time()
            msg = self.connection.recv_match(
                type=["LOCAL_POSITION_NED", "ATTITUDE"], blocking=True, timeout=remaining
            )
            if msg is None:
                continue

            if position_msg is None and msg.get_type() == "LOCAL_POSITION_NED":
                position_msg = msg
                self.logger.info("Received LOCAL_POSITION_NED", True)
            if attitude_msg is None and msg.get_type() == "ATTITUDE":
                attitude_msg = msg
                self.logger.info("Received ATTITUDE", True)

            if position_msg is not None and attitude_msg is not None:
                telemetry_data = TelemetryData(
                    time_since_boot=max(attitude_msg.time_boot_ms, position_msg.time_boot_ms),
                    x=position_msg.x,
                    y=position_msg.y,
                    z=position_msg.z,
                    x_velocity=position_msg.vx,
                    y_velocity=position_msg.vy,
                    z_velocity=position_msg.vz,
                    roll=attitude_msg.roll,
                    pitch=attitude_msg.pitch,
                    yaw=attitude_msg.yaw,
                    roll_speed=attitude_msg.rollspeed,
                    pitch_speed=attitude_msg.pitchspeed,
                    yaw_speed=attitude_msg.yawspeed,
                )
                self.logger.info("Created TelemetryData", True)
                return True, telemetry_data

        self.logger.error("Timeout: Did not receive both messages within 1 second", True)
        return False, None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
