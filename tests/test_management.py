import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import manage


class ManagementGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def mark(self, path=None):
        (self.path / manage.MARKER).write_text(json.dumps({"owner": manage.OWNER, "path": str(path or self.path)}))

    def test_unmanaged_install_is_not_adopted(self):
        with self.assertRaises(RuntimeError):
            manage.owned_install(self.path)

    def test_marker_must_match_exact_directory(self):
        self.mark(self.path / "other")
        with self.assertRaises(RuntimeError):
            manage.owned_install(self.path)

    def test_stop_cannot_close_another_windhawk(self):
        self.mark()
        with patch.object(manage, "require_windows"), patch.object(manage, "running_windhawk", return_value=[{"Path": "C:/Other/windhawk.exe"}]), patch.object(manage, "execute") as execute:
            with self.assertRaises(RuntimeError):
                manage.control(self.path, False)
            execute.assert_not_called()

    def test_uninstall_refuses_missing_marker(self):
        with patch.object(manage, "require_windows"), self.assertRaises(RuntimeError):
            manage.uninstall(self.path)
        self.assertTrue(self.path.exists())

    def test_installer_edition_must_use_its_own_uninstaller(self):
        self.mark()
        marker = self.path / manage.MARKER
        data = json.loads(marker.read_text())
        data["installerManaged"] = True
        marker.write_text(json.dumps(data))
        with patch.object(manage, "require_windows"), self.assertRaisesRegex(RuntimeError, "Uninstall.exe"):
            manage.uninstall(self.path)
        self.assertTrue(self.path.exists())

    def test_deploy_writes_backup_and_exact_bytes(self):
        self.mark()
        dest = self.path / "AppData/Engine/Mods/64/holidays.tsv"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"old dataset")
        manage.deploy_data(self.path)
        self.assertEqual(dest.with_suffix(".tsv.bak").read_bytes(), b"old dataset")
        self.assertEqual(dest.read_bytes(), (manage.ROOT / "data/holidays.tsv").read_bytes())
