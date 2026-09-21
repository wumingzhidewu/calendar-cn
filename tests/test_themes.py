import json
from pathlib import Path
import re
import unittest
from theme_presets import ROOT, load_catalog, style_rules


class Themes(unittest.TestCase):
    def test_twenty_complete_themes_and_three_modes(self):
        themes=load_catalog()
        self.assertEqual(len(themes),20)
        self.assertEqual(sum(t.get('collection')=='expressive' for t in themes),10)
        for theme in themes:
            self.assertTrue((ROOT/'themes/assets'/f'{theme["id"]}.jpg').is_file())
            for mode in ('art','gradient','solid'):
                preset=json.loads((ROOT/'themes/presets'/f'{theme["id"]}.{mode}.json').read_text(encoding='utf-8'))
                self.assertTrue(preset['controlStyles[0].target'].endswith('#CalendarCenterGrid'))

    def test_presets_do_not_replace_date_templates_or_holiday_data(self):
        for theme in load_catalog():
            for mode in ('art','gradient','solid'):
                for target,rules in style_rules(theme,mode):
                    self.assertNotIn('NotificationCenterPage',target)
                    self.assertNotIn('CalendarViewDayItem',target)
                    self.assertTrue(all(not r.startswith('Template') for r in rules))
                    self.assertTrue(all('http:' not in r and 'https:' not in r for r in rules))

    def test_text_contrast_against_flat_palette(self):
        def luminance(color):
            values=[int(color[n:n+2],16)/255 for n in (1,3,5)]
            values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
            return sum(a*b for a,b in zip(values,(.2126,.7152,.0722)))
        for theme in load_catalog():
            for bg in ('background','end'):
                a,b=sorted((luminance(theme['foreground']),luminance(theme[bg])))
                self.assertGreaterEqual((b+.05)/(a+.05),4.5,theme['id'])

    def test_october_preview_marks_exact_announced_dates(self):
        holidays=json.loads((ROOT/'data/years/2026.json').read_text(encoding='utf-8'))['days']
        october=[d for d in holidays if d['date'].startswith('2026-10')]
        self.assertEqual([d['date'] for d in october if not d['isOffDay']],['2026-10-10'])
        self.assertEqual({d['date'] for d in october if d['isOffDay']},{f'2026-10-{n:02d}' for n in range(1,8)})
        lunar=json.loads((ROOT/'docs/design/sample-lunar-dates.json').read_text(encoding='utf-8'))
        self.assertEqual(len(lunar),42)
        self.assertEqual(len({d['date'] for d in lunar}),42)

    def test_expressive_themes_have_distinct_complete_prompts(self):
        new=[t for t in load_catalog() if t.get('collection')=='expressive']
        prompts=[(ROOT/t['promptFile']).read_text(encoding='utf-8') for t in new]
        self.assertEqual(len(set(prompts)),10)
        for prompt in prompts:
            self.assertGreater(len(prompt),1800)
            self.assertIn('COMPOSITION:',prompt)
            self.assertIn('ART DIRECTION:',prompt)
            self.assertIn('No Chinese or Latin text',prompt)

    def test_existing_green_theme_is_still_available(self):
        moss=next(t for t in load_catalog() if t['id']=='moss-garden')
        self.assertEqual(moss['collection'],'classic')
        self.assertEqual(moss['background'],'#EEF3E8')
