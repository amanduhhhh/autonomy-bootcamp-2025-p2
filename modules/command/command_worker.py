"""
Command worker to make decisions based on Telemetry Data.
"""

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import command
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def command_worker(
    connection: mavutil.mavfile,
    target: command.Position,
    telemetry_queue: queue_proxy_wrapper.QueueProxyWrapper,
    output_queue: queue_proxy_wrapper.QueueProxyWrapper,
    controller: worker_controller.WorkerController,
) -> None:
    """
    Worker process.

    Args:
        connection: MAVLink connection to drone
        target: Target position for  command
        telemetry_queue: Telemetry receival queue
        output_queue: Command results queue
        controller: Controller for worker
    """
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Instantiate class object (command.Command)
    result, cmd = command.Command.create(connection, target, local_logger)
    if not result:
        local_logger.error("Failed to create Command", True)
        return
    local_logger.info("Command created", True)

    # Main loop: do work.
    while not controller.is_exit_requested():
        controller.check_pause()
        if telemetry_queue.queue.empty():
            continue

        telemetry_data = telemetry_queue.queue.get()
        local_logger.info("Received telemetry", True)
        if telemetry_data is None:
            continue

        result, cmd_action = cmd.run(telemetry_data)
        if result:
            output_queue.queue.put(cmd_action)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
