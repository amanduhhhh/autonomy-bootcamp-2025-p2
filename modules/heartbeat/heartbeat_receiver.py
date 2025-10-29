"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from tests.integration.mock_drones import heartbeat_receiver_drone

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
MAX_MISSED = heartbeat_receiver_drone.DISCONNECT_THRESHOLD
HEARTBEAT_TIMEOUT = heartbeat_receiver_drone.HEARTBEAT_PERIOD


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
    ) -> "tuple[True, HeartbeatReceiver] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        return True, cls(cls.__private_key, connection, local_logger)

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

    def run(self) -> "tuple[bool, str]":
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """
        msg = self.connection.recv_match(type="HEARTBEAT", blocking=True, timeout=HEARTBEAT_TIMEOUT)
        if msg and msg.get_type() == "HEARTBEAT":
            if not self.connected:
                self.connected = True
                self.local_logger.info("Connected to drone")
            self.missed = 0
        else:
            if self.connected:
                self.missed += 1
                self.local_logger.warning(f"{self.missed} heartbeats missed")
                if self.missed >= MAX_MISSED:
                    self.connected = False
                    self.local_logger.warning(
                        f"{MAX_MISSED} missed heartbeats - Disconnected from drone"
                    )
        status = "Connected" if self.connected else "Disconnected"
        return True, status


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
