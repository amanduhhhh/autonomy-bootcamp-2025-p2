"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import queue
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
HEARTBEAT_QUEUE_MAX_SIZE = 10
TELEMETRY_QUEUE_MAX_SIZE = 10
COMMAND_QUEUE_MAX_SIZE = 10

# Set worker counts
HEARTBEAT_SENDER_WORKER_COUNT = 1
HEARTBEAT_RECEIVER_WORKER_COUNT = 1
TELEMETRY_WORKER_COUNT = 1
COMMAND_WORKER_COUNT = 1

# Any other constants
LOOP_DURATION = 100
TARGET = command.Position(10, 20, 30)
# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller
    controller = worker_controller.WorkerController()

    # Create a multiprocess manager for synchronized queues
    mp_manager = mp.Manager()
    # Create queues
    heartbeat_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, HEARTBEAT_QUEUE_MAX_SIZE)
    telemetry_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, TELEMETRY_QUEUE_MAX_SIZE)
    command_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, COMMAND_QUEUE_MAX_SIZE)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender
    result, heartbeat_sender_props = worker_manager.WorkerProperties.create(
        num_workers=HEARTBEAT_SENDER_WORKER_COUNT,
        worker_function=heartbeat_sender_worker.heartbeat_sender_worker,
        worker_kwargs={
            "connection": connection,
            "controller": controller,
        },
        local_logger=main_logger,
    )
    if not result:
        main_logger.error("Failed to create heartbeat sender properties")
        return -1

    # Heartbeat receiver
    result, heartbeat_receiver_props = worker_manager.WorkerProperties.create(
        num_workers=HEARTBEAT_RECEIVER_WORKER_COUNT,
        worker_function=heartbeat_receiver_worker.heartbeat_receiver_worker,
        worker_kwargs={
            "connection": connection,
            "controller": controller,
        },
        local_logger=main_logger,
    )
    if not result:
        main_logger.error("Failed to create heartbeat receiver properties")
        return -1

    # Telemetry

    result, telemetry_props = worker_manager.WorkerProperties.create(
        num_workers=TELEMETRY_WORKER_COUNT,
        worker_function=telemetry_worker.telemetry_worker,
        worker_kwargs={
            "connection": connection,
            "controller": controller,
        },
        local_logger=main_logger,
    )
    if not result:
        main_logger.error("Failed to create telemetry properties")
        return -1

    # Command
    result, command_props = worker_manager.WorkerProperties.create(
        num_workers=COMMAND_WORKER_COUNT,
        worker_function=command_worker.command_worker,
        worker_kwargs={
            "connection": connection,
            "controller": controller,
        },
        local_logger=main_logger,
    )
    if not result:
        main_logger.error("Failed to create command properties")
        return -1

    # Create the workers (processes) and obtain their managers
    result, heartbeat_sender_managers = worker_manager.create_workers(heartbeat_sender_props)
    if not result:
        main_logger.error("Failed to create heartbeat sender managers")
        return -1
    result, heartbeat_receiver_managers = worker_manager.create_workers(heartbeat_receiver_props)
    if not result:
        main_logger.error("Failed to create heartbeat receiver managers")
        return -1
    result, telemetry_managers = worker_manager.create_workers(telemetry_props)
    if not result:
        main_logger.error("Failed to create telemetry managers")
        return -1
    result, command_managers = worker_manager.create_workers(command_props)
    if not result:
        main_logger.error("Failed to create command managers")
        return -1

    # Start worker processes
    heartbeat_sender_managers.start_workers()
    heartbeat_receiver_managers.start_workers()
    telemetry_managers.start_workers()
    command_managers.start_workers()

    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects

    # Stop the processes
    controller.request_exit()
    main_logger.info("Requested exit")

    # Fill and drain queues from END TO START
    command_queue.fill_and_drain_queue()
    telemetry_queue.fill_and_drain_queue()
    heartbeat_queue.fill_and_drain_queue()

    main_logger.info("Queues cleared")

    # Clean up worker processes
    command_managers.join_workers()
    telemetry_managers.join_workers()
    heartbeat_receiver_managers.join_workers()
    heartbeat_sender_managers.join_workers()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance
    controller.clear_exit()

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")
