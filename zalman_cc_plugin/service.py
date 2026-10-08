"""CoolerControl device service exposing the Zalman ALPHA2 DS LCD.

CoolerControl preprocesses LCD images itself and hands us the resulting file
path; this service only forwards brightness, orientation and images to
zalman_lcd.LcdClient. The device has no fans, lights or sensors here.
"""

import logging
import threading
import time

import grpc

from coolercontrol.device_service.v1 import (
    custom_function_one_pb2,
    device_service_pb2_grpc,
    enable_manual_fan_control_pb2,
    fixed_duty_pb2,
    health_pb2,
    initialize_device_pb2,
    lcd_pb2,
    lighting_pb2,
    list_devices_pb2,
    reset_channel_pb2,
    shutdown_pb2,
    speed_profile_pb2,
    status_pb2,
)
from coolercontrol.models.v1 import (
    channel_info_pb2,
    device_info_pb2,
    device_pb2,
    driver_info_pb2,
    lcd_info_pb2,
)
from zalman_lcd.client import LcdClient
from zalman_lcd.device import DeviceError, find_tty

from . import __version__

_LOG = logging.getLogger(__name__)

SERVICE_NAME = "zalman-lcd"
DEVICE_ID = "zalman-alpha2-lcd"
CHANNEL_ID = "lcd"
SCREEN_SIZE = 320
# Upper bound CoolerControl enforces on processed images it hands us.
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024


class ZalmanDeviceService(device_service_pb2_grpc.DeviceServiceServicer):
    def __init__(self, stop_event: threading.Event) -> None:
        self._stop_event = stop_event
        self._started = time.monotonic()
        self._client = LcdClient()

    # --- lifecycle -------------------------------------------------------

    def Health(
        self, request: health_pb2.HealthRequest, context: grpc.ServicerContext
    ) -> health_pb2.HealthResponse:
        status = (
            health_pb2.HealthResponse.STATUS_OK
            if find_tty() is not None
            else health_pb2.HealthResponse.STATUS_WARNING
        )
        return health_pb2.HealthResponse(
            name=SERVICE_NAME,
            version=__version__,
            status=status,
            uptime_seconds=int(time.monotonic() - self._started),
        )

    def ListDevices(
        self, request: list_devices_pb2.ListDevicesRequest, context: grpc.ServicerContext
    ) -> list_devices_pb2.ListDevicesResponse:
        tty = find_tty()
        if tty is None:
            _LOG.warning("Zalman LCD not present; reporting no devices")
            return list_devices_pb2.ListDevicesResponse()
        lcd_info = lcd_info_pb2.LcdInfo(
            screen_width=SCREEN_SIZE,
            screen_height=SCREEN_SIZE,
            max_image_size_bytes=MAX_IMAGE_SIZE_BYTES,
            lcd_modes=[
                lcd_info_pb2.LcdInfo.LcdModes(
                    name="image",
                    frontend_name="Image/gif",
                    brightness=True,
                    orientation=True,
                    image=True,
                )
            ],
        )
        device = device_pb2.Device(
            id=DEVICE_ID,
            name="Zalman ALPHA2 LCD",
            uid_info="usb-0483:5740-HWCX-TECH_USB_Display",
            info=device_info_pb2.DeviceInfo(
                channels={CHANNEL_ID: channel_info_pb2.ChannelInfo(label="LCD", lcd_info=lcd_info)},
                model="Zalman ALPHA2 DS LCD Display",
                driver_info=driver_info_pb2.DriverInfo(
                    name="zalman_lcd (cdc_acm)",
                    version=__version__,
                    locations=[tty],
                ),
            ),
        )
        return list_devices_pb2.ListDevicesResponse(devices=[device])

    def InitializeDevice(
        self, request: initialize_device_pb2.InitializeDeviceRequest, context: grpc.ServicerContext
    ) -> initialize_device_pb2.InitializeDeviceResponse:
        self._check_device(request.device_id, context)
        # Also called after resume: drop any stale serial handle so the next
        # command reconnects and re-wakes the panel.
        self._client.close()
        return initialize_device_pb2.InitializeDeviceResponse()

    def Shutdown(
        self, request: shutdown_pb2.ShutdownRequest | None, context: grpc.ServicerContext | None
    ) -> shutdown_pb2.ShutdownResponse:
        _LOG.info("Shutdown requested by CoolerControl")
        self._client.close()
        self._stop_event.set()
        return shutdown_pb2.ShutdownResponse()

    def Status(
        self, request: status_pb2.StatusRequest, context: grpc.ServicerContext
    ) -> status_pb2.StatusResponse:
        self._check_device(request.device_id, context)
        return status_pb2.StatusResponse()

    # --- LCD -------------------------------------------------------------

    def Lcd(
        self, request: lcd_pb2.LcdRequest, context: grpc.ServicerContext
    ) -> lcd_pb2.LcdResponse:
        self._check_device(request.device_id, context)
        self._check_channel(request.channel_id, context)
        setting = request.setting
        _LOG.debug("LCD request: %s", setting)
        if setting.mode not in ("image", "none"):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Unsupported LCD mode: {setting.mode}")
        try:
            if setting.mode == "none":
                # CoolerControl always offers "None": blank the panel.
                self._client.set_color("000000")
                return lcd_pb2.LcdResponse()
            if setting.HasField("brightness"):
                self._client.set_brightness(setting.brightness)
            if setting.HasField("orientation"):
                # CoolerControl means clockwise; LcdClient (PIL) rotates counter-clockwise.
                self._client.set_orientation((360 - setting.orientation) % 360)
            if setting.HasField("image_path"):
                self._client.set_image(setting.image_path)
        except (OSError, DeviceError, ValueError) as err:
            _LOG.error("LCD update failed: %s", err)
            context.abort(grpc.StatusCode.UNAVAILABLE, f"LCD update failed: {err}")
        return lcd_pb2.LcdResponse()

    def ResetChannel(
        self, request: reset_channel_pb2.ResetChannelRequest, context: grpc.ServicerContext
    ) -> reset_channel_pb2.ResetChannelResponse:
        self._check_device(request.device_id, context)
        self._check_channel(request.channel_id, context)
        return reset_channel_pb2.ResetChannelResponse()

    # --- unsupported channel types ---------------------------------------

    def EnableManualFanControl(
        self,
        request: enable_manual_fan_control_pb2.EnableManualFanControlRequest,
        context: grpc.ServicerContext,
    ) -> enable_manual_fan_control_pb2.EnableManualFanControlResponse:
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "No fan channels")
        return enable_manual_fan_control_pb2.EnableManualFanControlResponse()

    def FixedDuty(
        self, request: fixed_duty_pb2.FixedDutyRequest, context: grpc.ServicerContext
    ) -> fixed_duty_pb2.FixedDutyResponse:
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "No fan channels")
        return fixed_duty_pb2.FixedDutyResponse()

    def SpeedProfile(
        self, request: speed_profile_pb2.SpeedProfileRequest, context: grpc.ServicerContext
    ) -> speed_profile_pb2.SpeedProfileResponse:
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "No fan channels")
        return speed_profile_pb2.SpeedProfileResponse()

    def Lighting(
        self, request: lighting_pb2.LightingRequest, context: grpc.ServicerContext
    ) -> lighting_pb2.LightingResponse:
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "No lighting channels")
        return lighting_pb2.LightingResponse()

    def CustomFunctionOne(
        self,
        request: custom_function_one_pb2.CustomFunctionOneRequest,
        context: grpc.ServicerContext,
    ) -> custom_function_one_pb2.CustomFunctionOneResponse:
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "Not supported")
        return custom_function_one_pb2.CustomFunctionOneResponse()

    # --- helpers ---------------------------------------------------------

    @staticmethod
    def _check_device(device_id: str, context: grpc.ServicerContext) -> None:
        if device_id != DEVICE_ID:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown device: {device_id}")

    @staticmethod
    def _check_channel(channel_id: str, context: grpc.ServicerContext) -> None:
        if channel_id != CHANNEL_ID:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown channel: {channel_id}")
