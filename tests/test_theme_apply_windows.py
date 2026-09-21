"""Exercise the actual PowerShell theme writer against an isolated fake install."""
import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell integration test')
class ThemeApplication(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='calendar-theme-test-')
        self.addCleanup(self.temp.cleanup)
        self.runtime=Path(self.temp.name)/'带 空格'
        mods=self.runtime/'AppData/Engine/Mods'
        mods.mkdir(parents=True)
        self.ini=mods/'local-native-calendar-holidays.ini'
        self.ini.write_text('[Mod]\nLibraryFileName=native-calendar-holidays.dll\nInclude=ShellExperienceHost.exe\nVersion=7.7.7\n[Settings]\ntheme=\ncustomPreserved=keep\n',encoding='utf-16')
        (self.runtime/'.native-calendar-holidays.json').write_text(json.dumps({'owner':'native-calendar-holidays-project-v1','path':str(self.runtime)}),encoding='utf-8')
        (self.runtime/'holidays.tsv').write_bytes(b'unchanged-holiday-data')
        shutil.copytree(ROOT/'themes',self.runtime/'themes')
        self.script=self.runtime/'Theme.ps1'
        self.script.write_text((ROOT/'installer/Theme.ps1').read_text(encoding='utf-8-sig'),encoding='utf-8-sig')

    def apply(self,theme,mode='art'):
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','RemoteSigned','-File',str(self.script),'-Action','Apply','-RuntimePath',str(self.runtime),'-ThemeId',theme,'-BackgroundMode',mode],capture_output=True)

    def read(self):
        parser=configparser.ConfigParser(interpolation=None)
        parser.read(self.ini,encoding='utf-16')
        return parser

    def test_apply_art_then_restore_original_settings(self):
        outcome=self.apply('moon-ink')
        error=self.runtime/'last-error.txt'
        self.assertEqual(outcome.returncode,0,error.read_text(encoding='utf-8-sig') if error.exists() else outcome.stderr)
        applied=self.read()
        self.assertEqual(applied['Mod']['Version'],'7.7.7')
        self.assertIn('file:///',applied['Settings']['controlStyles[0].styles[0]'])
        self.assertIn('%20',applied['Settings']['controlStyles[0].styles[0]'])
        before=int(applied['Mod']['SettingsChangeTime'])
        self.assertEqual(self.apply('system').returncode,0)
        restored=self.read()
        self.assertEqual(restored['Settings']['customPreserved'],'keep')
        self.assertFalse(any(key.startswith('controlstyles[') for key in restored['Settings']))
        self.assertGreater(int(restored['Mod']['SettingsChangeTime']),before)
        self.assertEqual((self.runtime/'holidays.tsv').read_bytes(),b'unchanged-holiday-data')

    def test_background_modes_and_selection_persist(self):
        self.assertEqual(self.apply('midnight-tide','gradient').returncode,0)
        self.assertIn('LinearGradientBrush',self.read()['Settings']['controlStyles[0].styles[0]'])
        self.assertEqual(self.apply('midnight-tide','solid').returncode,0)
        self.assertEqual(self.read()['Settings']['controlStyles[0].styles[0]'],'Background=#102536')
        selected=json.loads((self.runtime/'selected-theme.json').read_text(encoding='utf-8'))
        self.assertEqual((selected['id'],selected['backgroundMode']),('midnight-tide','solid'))

    def test_invalid_theme_does_not_change_mod_config(self):
        old=self.ini.read_bytes()
        self.assertNotEqual(self.apply('../unknown').returncode,0)
        self.assertEqual(self.ini.read_bytes(),old)
