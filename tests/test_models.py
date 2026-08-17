"""Tests for redacted Circle response parsing."""

import ast
import importlib.util
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "myfirst_circle" / "models.py"
)
SPEC = importlib.util.spec_from_file_location("circle_models", MODULE_PATH)
assert SPEC and SPEC.loader
models = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = models
SPEC.loader.exec_module(models)


class CircleModelTests(unittest.TestCase):
    def test_anonymous_client_seed_shape(self) -> None:
        const_path = MODULE_PATH.with_name("const.py")
        module = ast.parse(const_path.read_text())
        assignments = {
            target.id: ast.literal_eval(node.value)
            for node in module.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
            and target.id in {"CLIENT_PREFIX_LENGTH", "DEFAULT_CLIENT_AUTHORIZATION"}
        }
        authorization = assignments["DEFAULT_CLIENT_AUTHORIZATION"]
        prefix_length = assignments["CLIENT_PREFIX_LENGTH"]
        self.assertEqual(prefix_length, 18)
        self.assertEqual(len(authorization), 168)
        self.assertEqual(len(authorization) - prefix_length, 150)

    def test_device_identifier_does_not_expose_imei(self) -> None:
        imei = "device-id"
        identifier = models.device_identifier(imei)
        self.assertNotIn(imei, identifier)
        self.assertEqual(len(identifier), 64)

    def test_parse_children(self) -> None:
        children = models.parse_children(
            {
                "code": 200,
                "data": {"listItem": [{"token": "child-token", "name": "Kid"}]},
            }
        )
        self.assertEqual(children[0].token, "child-token")
        self.assertEqual(children[0].name, "Kid")

    def test_parse_devices(self) -> None:
        devices = models.parse_devices(
            {
                "data": {
                    "Devices": [
                        {
                            "IMEI": "device-id",
                            "DeviceModel": "Watch model",
                            "Manufacture": "myFirst",
                        }
                    ]
                }
            },
            child_token="child-token",
            child_name="Kid",
        )
        self.assertEqual(devices[0].imei, "device-id")
        self.assertEqual(devices[0].user_token, "child-token")
        self.assertEqual(devices[0].child_name, "Kid")

    def test_build_location_refresh_payload(self) -> None:
        device = models.CircleDevice(
            imei="device-id",
            user_token="child-token",
            child_name="Kid",
        )
        self.assertEqual(
            models.build_location_refresh_payload(device, 1_700_000_000_000),
            {
                "devicetype": "WATCH",
                "imei": "device-id",
                "langID": "en",
                "refreshlocation": "1700000000000",
                "token": "child-token",
            },
        )

    def test_parse_device_info(self) -> None:
        now = datetime.now(UTC)
        info = models.parse_device_info(
            {
                "data": {
                    "imei": "device-id",
                    "latitude": 1.25,
                    "longitude": 2.5,
                    "battery": 74,
                    "enablesmartloc": True,
                    "devicestatus": {"ischarging": False, "isturnedon": True},
                }
            },
            retrieved_at=now,
        )
        self.assertEqual(info.latitude, 1.25)
        self.assertEqual(info.longitude, 2.5)
        self.assertEqual(info.battery, 74)
        self.assertTrue(info.is_turned_on)
        self.assertEqual(info.retrieved_at, now)

    def test_missing_data_is_rejected(self) -> None:
        with self.assertRaises(models.CirclePayloadError):
            models.parse_children({"code": 200})

    def test_parse_login_session(self) -> None:
        session = models.parse_session(
            {
                "code": 200,
                "data": {
                    "authtoken": "encrypted-api-token",
                    "token": "parent-token",
                    "data": {"token": "nested-parent-token"},
                },
            }
        )
        self.assertEqual(session.api_token, "encrypted-api-token")
        self.assertEqual(session.user_token, "parent-token")

    def test_parse_refresh_session(self) -> None:
        session = models.parse_session(
            {
                "code": 200,
                "data": {
                    "authtoken": "refreshed-api-token",
                    "usertoken": "parent-token",
                },
            }
        )
        self.assertEqual(session.api_token, "refreshed-api-token")
        self.assertEqual(session.user_token, "parent-token")


if __name__ == "__main__":
    unittest.main()
