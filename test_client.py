#!/usr/bin/env python3
"""Talk to a running plugin the way CoolerControl does (step 2 test).

Usage: python test_client.py SOCKET IMAGE [--brightness N] [--orientation DEG]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "zalman_cc_plugin" / "gen"))

import grpc  # noqa: E402

from coolercontrol.device_service.v1 import (  # noqa: E402
    device_service_pb2_grpc,
    health_pb2,
    initialize_device_pb2,
    lcd_pb2,
    list_devices_pb2,
    status_pb2,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("socket")
    p.add_argument("image")
    p.add_argument("--brightness", type=int, default=80)
    p.add_argument("--orientation", type=int, default=0)
    a = p.parse_args()

    with grpc.insecure_channel(f"unix://{a.socket}") as channel:
        stub = device_service_pb2_grpc.DeviceServiceStub(channel)
        print("Health:", stub.Health(health_pb2.HealthRequest()), sep="\n")
        devices = stub.ListDevices(list_devices_pb2.ListDevicesRequest()).devices
        print("ListDevices:", devices, sep="\n")
        if not devices:
            sys.exit("no device reported")
        dev = devices[0]
        stub.InitializeDevice(initialize_device_pb2.InitializeDeviceRequest(device_id=dev.id))
        print("Status:", stub.Status(status_pb2.StatusRequest(device_id=dev.id)))
        setting = lcd_pb2.LcdSetting(
            mode="image",
            brightness=a.brightness,
            orientation=a.orientation,
            image_path=str(Path(a.image).resolve()),
        )
        stub.Lcd(lcd_pb2.LcdRequest(device_id=dev.id, channel_id="lcd", setting=setting))
        print("Lcd: OK")


if __name__ == "__main__":
    main()
