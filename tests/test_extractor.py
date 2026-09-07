import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
from unittest import mock
import xml.etree.ElementTree as ET

import auto_extract_notes_ultimate as extractor


class ExtractorTests(unittest.TestCase):
    def tearDown(self):
        extractor.ADB = None
        extractor.DEVICE_SERIAL = None

    def test_import_has_no_device_side_effects(self):
        self.assertIsNone(extractor.ADB)

    def test_get_note_parses_one_snapshot_and_uses_full_identity(self):
        root = ET.fromstring(
            '<hierarchy><node package="com.huawei.notepad" '
            'resource-id="com.huawei.notepad:id/title" text="标题" />'
            '<node package="com.huawei.notepad" '
            'resource-id="com.huawei.notepad:id/notecontent_date_text" text="2026-09-07" />'
            '<node package="com.huawei.notepad" '
            'resource-id="com.huawei.notepad:id/notetext_textview" text="正文&#10;第二行" />'
            "</hierarchy>"
        )
        with mock.patch.object(extractor, "dump_ui", return_value=root) as dump:
            title, content, identity = extractor.get_note()
        self.assertEqual(title, "标题 - 2026-09-07")
        self.assertEqual(content, "正文\n第二行")
        self.assertEqual(len(identity), 64)
        dump.assert_called_once_with()

    def test_list_title_alone_is_not_mistaken_for_detail_page(self):
        root = ET.fromstring(
            '<hierarchy><node package="com.huawei.notepad" '
            'resource-id="com.huawei.notepad:id/title" text="列表标题" /></hierarchy>'
        )
        with mock.patch.object(extractor, "dump_ui", return_value=root):
            self.assertIsNone(extractor.get_note())

    def test_empty_handwritten_note_is_valid_when_timestamp_is_present(self):
        root = ET.fromstring(
            '<hierarchy><node package="com.huawei.notepad" '
            'resource-id="com.huawei.notepad:id/notecontent_date_text" text="现在" /></hierarchy>'
        )
        with mock.patch.object(extractor, "dump_ui", return_value=root):
            title, content, _identity = extractor.get_note()
        self.assertEqual(title, "未知 - 现在")
        self.assertEqual(content, "")

    def test_safe_name_blocks_paths_shell_metacharacters_and_empty_names(self):
        self.assertEqual(extractor.safe_name('../bad";name'), "_bad_;name")
        self.assertEqual(extractor.safe_name("..."), "华为备忘录导出")
        self.assertNotIn("/", extractor.safe_name("a/b"))
        self.assertEqual(extractor.safe_name("CON"), "_CON")
        self.assertEqual(extractor.safe_name("CON.txt"), "_CON.txt")
        self.assertEqual(extractor.safe_name("LPT1.backup"), "_LPT1.backup")
        self.assertEqual(extractor.safe_name("notes. "), "notes")

    def test_check_device_locks_subsequent_commands_to_authorized_serial(self):
        extractor.ADB = "adb"
        devices = subprocess.CompletedProcess(
            [],
            0,
            stdout=(
                "List of devices attached\n"
                "phone-serial\tdevice\n"
                "pending-serial\tunauthorized\n"
            ),
            stderr="",
        )
        with mock.patch("subprocess.run", return_value=devices):
            extractor.check_device()

        self.assertEqual(extractor.DEVICE_SERIAL, "phone-serial")

        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch("subprocess.run", return_value=completed) as run:
            extractor.adb(["input", "tap", "1", "2"])
        self.assertEqual(
            run.call_args.args[0],
            ["adb", "-s", "phone-serial", "shell", "input", "tap", "1", "2"],
        )

    def test_unused_path_never_overwrites_existing_export(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "notes.txt"
            first.write_text("keep", encoding="utf-8")
            second = extractor.unused_path(first)
            self.assertEqual(second.name, "notes_1.txt")
            self.assertEqual(first.read_text(encoding="utf-8"), "keep")

    def test_unused_path_does_not_follow_a_broken_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "notes.txt"
            try:
                first.symlink_to(Path(directory) / "missing-target.txt")
            except OSError as exc:
                self.skipTest(f"symlinks are unavailable: {exc}")
            second = extractor.unused_path(first)
            self.assertEqual(second.name, "notes_1.txt")

    def test_adb_uses_argument_list_and_surfaces_failure(self):
        extractor.ADB = "adb"
        completed = subprocess.CompletedProcess(
            [], 1, stdout="", stderr="device offline"
        )
        with mock.patch("subprocess.run", return_value=completed) as run:
            with self.assertRaisesRegex(extractor.ExtractionError, "device offline"):
                extractor.adb(["input", "tap", "1", "2"])
        self.assertEqual(
            run.call_args.args[0], ["adb", "shell", "input", "tap", "1", "2"]
        )
        self.assertNotIn("shell", run.call_args.kwargs)
        extractor.ADB = None

    def test_ui_signature_ignores_status_bar_but_detects_list_changes(self):
        one = ET.fromstring(
            '<hierarchy><node package="android" text="12:00" />'
            '<node package="com.huawei.notepad" text="A" bounds="[0,0][1,1]" /></hierarchy>'
        )
        two = ET.fromstring(
            '<hierarchy><node package="android" text="12:01" />'
            '<node package="com.huawei.notepad" text="A" bounds="[0,0][1,1]" /></hierarchy>'
        )
        moved = ET.fromstring(
            '<hierarchy><node package="android" text="12:01" />'
            '<node package="com.huawei.notepad" text="B" bounds="[0,0][1,1]" /></hierarchy>'
        )
        self.assertEqual(extractor.ui_signature(one), extractor.ui_signature(two))
        self.assertNotEqual(extractor.ui_signature(one), extractor.ui_signature(moved))

    def test_screenshot_path_is_passed_as_one_argument_without_shell(self):
        extractor.ADB = "adb"
        extractor.DEVICE_SERIAL = "phone-serial"
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'note";echo unsafe.png'

            def fake_run(args, **_kwargs):
                Path(args[-1]).touch()
                return subprocess.CompletedProcess(args, 0, "ok", "")

            with (
                mock.patch.object(extractor, "adb"),
                mock.patch("subprocess.run", side_effect=fake_run) as run,
            ):
                extractor.take_screenshot(destination)
            self.assertEqual(
                run.call_args.args[0],
                [
                    "adb",
                    "-s",
                    "phone-serial",
                    "pull",
                    "/sdcard/temp_screenshot.png",
                    str(destination),
                ],
            )
            self.assertNotIn("shell", run.call_args.kwargs)
        extractor.ADB = None

    def test_full_mode_preserves_short_notes_stops_and_avoids_overwrite(self):
        list_a = ET.fromstring(
            '<hierarchy><node package="com.huawei.notepad" text="A" /></hierarchy>'
        )
        list_b = ET.fromstring(
            '<hierarchy><node package="com.huawei.notepad" text="B" /></hierarchy>'
        )
        note_one = ("短记录 - 现在", "好", "one")
        note_two = ("普通记录 - 稍后", "正文", "two")
        dump_sequence = [
            list_a,
            list_a,
            list_b,
            list_b,
            list_b,
            list_b,
            list_b,
            list_b,
            list_b,
        ]

        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                Path("notes.txt").write_text("existing export", encoding="utf-8")
                with (
                    mock.patch.object(extractor, "find_adb", return_value="adb"),
                    mock.patch.object(extractor, "check_device"),
                    mock.patch.object(
                        extractor, "get_folder_name", return_value="folder"
                    ),
                    mock.patch.object(extractor, "tap"),
                    mock.patch.object(extractor, "back"),
                    mock.patch.object(extractor, "swipe_one_item"),
                    mock.patch.object(extractor, "dump_ui", side_effect=dump_sequence),
                    mock.patch.object(
                        extractor,
                        "get_note",
                        side_effect=[note_one, note_two, note_two, note_two, None],
                    ),
                    mock.patch(
                        "builtins.input", side_effect=["invalid", "1", "notes", ""]
                    ),
                    redirect_stdout(io.StringIO()),
                ):
                    extractor.main()
                exported = Path("notes_1.txt").read_text(encoding="utf-8")
                self.assertIn("短记录", exported)
                self.assertIn("好", exported)
                self.assertIn("普通记录", exported)
                self.assertEqual(
                    Path("notes.txt").read_text(encoding="utf-8"), "existing export"
                )
            finally:
                os.chdir(previous)
                extractor.ADB = None


if __name__ == "__main__":
    unittest.main()
