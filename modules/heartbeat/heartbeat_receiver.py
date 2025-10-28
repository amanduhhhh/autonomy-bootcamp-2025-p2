"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from tests.integration.mock_drones import heartbeat_receiver_drone

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
MAX_MISSED = 5
HEARTBEAT_TIMEOUT = 1.0


class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> "tuple":
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        try:
            heartbeat_receiver = cls(cls.__private_key, connection, local_logger)
            return True, heartbeat_receiver
        except Exception as error:
            local_logger.error(f"Failed to create HeartbeatReceiver object: {error}")
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        self.connection = connection
        self.local_logger = local_logger
        self.connected = False
        self.missed = 0

    def run(self) -> "tuple":
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """
        try:
            msg = self.connection.recv_match(
                type="HEARTBEAT", blocking=False, timeout=HEARTBEAT_TIMEOUT
            )
            if msg:
                if not self.connected:
                    self.connected = True
                    self.local_logger.info("Connected to drone")
                self.last = msg.time_usec
                self.missed = 0
            else:
                if self.connected:
                    self.missed += 1
                    self.local_logger.info(f"{self.missed} heartbeats missed")
                    if self.missed >= MAX_MISSED:
                        self.connected = False
                        self.local_logger.info(
                            f"{MAX_MISSED} missed heartbeats - Disconnected from drone"
                        )
            status = "Connected" if self.connected else "Disconnected"
            return True, status

        except Exception as error:
            self.local_logger.error(f"Failed to receive heartbeat: {error}")
            return False, f"Failed to receive heartbeat: {error}"


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
