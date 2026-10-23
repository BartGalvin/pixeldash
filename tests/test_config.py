from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from pixeldash.config import Config, DEFAULTS
from support import ConfiguredTestCase


class ConfigTests(ConfiguredTestCase):
    def test_defaults_work_without_a_config_file(self):
        output = StringIO()
        with redirect_stdout(output):
            config = Config()
        self.assertEqual(config.get("display.width"), 64)
        self.assertEqual(output.getvalue(), "")
        self.assertTrue(Path(config.get("font.path")).is_file())

    def test_nested_overrides_do_not_mutate_defaults(self):
        self.configure_with("display: {width: 128}\n")
        self.assertEqual(Config().get("display.width"), 64)
        self.assertEqual(DEFAULTS["display"]["width"], 64)

    def test_local_file_overrides_only_its_own_values(self):
        Path("config.yaml").write_text("display: {width: 128}\nclock: {show_date: false}\n")
        Path("config.local.yaml").write_text("display: {width: 192}\n")
        config = Config()
        self.assertEqual(config.get("display.width"), 192)
        self.assertEqual(config.get("display.height"), 32)
        self.assertFalse(config.get("clock.show_date"))

    def test_explicit_file_ignores_other_files(self):
        Path("config.local.yaml").write_text("display: {width: 192}\n")
        config = self.configure_with("clock: {show_date: false}\n")
        self.assertEqual(config.get("display.width"), 64)

    def test_explicit_missing_file_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            Config("missing.yaml")

    def test_empty_file_uses_defaults(self):
        config = self.configure_with("")
        self.assertEqual(config.get("dashboard.screens"), ["clock", "hello"])

    def test_invalid_settings_fail_before_startup(self):
        for text in (
            "[clock, hello]", "display: null", "display: {width: 0}",
            "emulator: {pixel_size: true}", "font: {size: '5'}",
            "dashboard: {interval: .nan}", "dashboard: {screens: []}",
            "dashboard: {screens: clock}", "clock: {format_24h: 'false'}",
            "weather: {units: kelvin}",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.configure_with(text)

    def test_yaml_error_does_not_echo_credential_contents(self):
        with self.assertRaisesRegex(ValueError, "Invalid YAML") as error:
            self.configure_with("weather: [private-test-credential\n")
        self.assertNotIn("private-test-credential", str(error.exception))
