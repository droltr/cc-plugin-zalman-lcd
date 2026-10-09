"""Entry point: python -m zalman_cc_plugin --socket /run/coolercontrol-plugin-zalman-lcd.sock"""

import argparse
import logging
import os
import signal
import sys
import threading
from concurrent import futures
from pathlib import Path

# Generated gRPC code uses absolute "coolercontrol.*" imports.
sys.path.insert(0, str(Path(__file__).resolve().parent / "gen"))

import grpc  # noqa: E402

from coolercontrol.device_service.v1 import device_service_pb2_grpc  # noqa: E402

from .service import ZalmanDeviceService  # noqa: E402

# CoolerControl passes its own log level in CC_LOG (ERROR/WARN/INFO/DEBUG/TRACE).
_LEVELS = {
    "ERROR": logging.ERROR,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "TRACE": logging.DEBUG,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CoolerControl device service for the Zalman ALPHA2 LCD"
    )
    parser.add_argument(
        "--socket",
        default="/run/coolercontrol-plugin-zalman-lcd.sock",
        help="Unix socket path to listen on (must match manifest address)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=_LEVELS.get(os.environ.get("CC_LOG", "INFO").upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("zalman_cc_plugin")

    socket_path = Path(args.socket)
    socket_path.unlink(missing_ok=True)

    stop_event = threading.Event()
    service = ZalmanDeviceService(stop_event)
    # One worker: the LCD is a single serial port and commands must not interleave.
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    device_service_pb2_grpc.add_DeviceServiceServicer_to_server(service, server)
    server.add_insecure_port(f"unix://{socket_path}")
    server.start()
    log.info("Listening on %s", socket_path)

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop_event.set())
    stop_event.wait()

    log.info("Stopping")
    server.stop(grace=2).wait()
    service.Shutdown(None, None)
    socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
