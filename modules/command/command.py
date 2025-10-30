"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry import telemetry


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
HEIGHT_TOLERANCE_M = 0.5
ANGLE_TOLERANCE = math.radians(5.0)
YAW_SPEED_DEG = 5.0
TARGET_SYSTEM = 1
TARGET_COMPONENT = 0


class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> "tuple[True, Command] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Command object.
        """
        return True, cls(cls.__private_key, connection, target, local_logger)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.target = target
        self.local_logger = local_logger

        self.vx_sum = 0.0
        self.vy_sum = 0.0
        self.vz_sum = 0.0
        self.count = 0

    def run(
        self, telemetry_data: telemetry.TelemetryData
    ) -> "tuple[True, str] | tuple[False, None]":
        """
        Make a decision based on received telemetry data.
        """
        # Log average velocity for this trip so far
        vx, vy, vz = telemetry_data.x_velocity, telemetry_data.y_velocity, telemetry_data.z_velocity
        self.vx_sum += vx
        self.vy_sum += vy
        self.vz_sum += vz
        self.count += 1
        avg_vx = self.vx_sum / self.count
        avg_vy = self.vy_sum / self.count
        avg_vz = self.vz_sum / self.count
        self.local_logger.info(
            f"Average velocity: ({avg_vx:.2f}, {avg_vy:.2f}, {avg_vz:.2f}) m/s", True
        )

        dist_z = self.target.z - telemetry_data.z
        if telemetry_data.z is not None and abs(dist_z) > HEIGHT_TOLERANCE_M:
            self.connection.mav.command_long_send(
                TARGET_SYSTEM,
                TARGET_COMPONENT,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,
                1.0,
                0,
                0,
                0,
                0,
                0,
                self.target.z,
            )
            self.local_logger.info(f"Changed altitude {dist_z:.2f} m", True)
            return True, f"Changed altitude {dist_z:.2f} m"

        if telemetry_data.yaw is not None:
            dist_x = self.target.x - telemetry_data.x
            dist_y = self.target.y - telemetry_data.y
            yaw_diff = (math.atan2(dist_y, dist_x) - telemetry_data.yaw + math.pi) % (
                2 * math.pi
            ) - math.pi

            if abs(yaw_diff) > ANGLE_TOLERANCE:
                yaw_diff_deg = math.degrees(yaw_diff)
                if yaw_diff_deg >= 0:
                    direction = 1
                else:
                    direction = -1
                self.connection.mav.command_long_send(
                    TARGET_SYSTEM,
                    TARGET_COMPONENT,
                    mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                    0,
                    yaw_diff_deg,
                    YAW_SPEED_DEG,
                    direction,
                    1,
                    0,
                    0,
                    0,
                    0,
                )
                self.local_logger.info(f"Changed yaw {yaw_diff_deg:.2f} degrees", True)
                return True, f"Changed yaw {yaw_diff_deg:.2f} degrees"
        return False, None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
