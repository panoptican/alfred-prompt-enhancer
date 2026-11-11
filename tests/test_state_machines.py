"""Offline process-level regressions; no accounts, notifications or real clipboard.

Run: python3 -m unittest discover -s tests -v
The fixture copies the shipped script, replacing only OS side effects and PATH.
"""
import os
import plistlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='prompt-enhancer-test-')
        self.addCleanup(self.cleanup_fixture)
        self.gates = []
        self.root = Path(self.tmp.name)
        self.wf = self.root / 'workflow'
        shutil.copytree(ROOT / 'workflow', self.wf)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.cache = self.root / 'cache'
        self.clip = self.root / 'clipboard'
        self.events = self.root / 'events'
        self.write_bin('osascript', '''#!/usr/bin/python3
import os,sys
with open(os.environ['EVENTS'], 'a') as f: f.write('|'.join(sys.argv[1:])+'\\n')
''')
        self.write_bin('afplay', '#!/bin/sh\nexit 0\n')
        self.write_bin('sleep', '#!/bin/sh\nprintf "%s\\n" "$1" >> "$DELAYS"\n')
        self.write_bin('pbcopy', '''#!/usr/bin/python3
import os,sys
if os.environ.get('COPY_FAIL'): sys.exit(1)
open(os.environ['CLIP'], 'w').write(sys.stdin.read())
''')
        self.cli = self.write_bin('model', '''#!/usr/bin/python3
import os,sys,time,pathlib
if sys.argv[1] == 'auth':
 print('{"loggedIn": false}' if os.environ.get('AUTH_FALSE') else '{"loggedIn": true}')
 sys.exit(1 if os.environ.get('AUTH_FALSE') else 0)
if sys.argv[1] == 'login': sys.exit(0)
sys.stdin.read()
count=pathlib.Path('attempts')
n=int(count.read_text())+1 if count.exists() else 1
count.write_text(str(n))
if os.environ.get('GATE'):
 gate=pathlib.Path(os.environ['GATE'])
 gate.with_suffix('.ready').touch()
 while not gate.exists(): time.sleep(.01)
behavior=os.environ.get('BEHAVIOR','ok')
if behavior in ('busy','busy-zero') and n < int(os.environ.get('SUCCEED_AT','3')):
 print('API Error: 529 overloaded')
 sys.exit(0 if behavior == 'busy-zero' else 1)
if behavior == 'failed':
 print('partial text'); sys.exit(1)
text={'blank':'   \\n\\t', 'empty':'', 'quoted':'Explain the string API Error: in this log.'}.get(behavior,os.environ.get('RESULT','rewritten prompt'))
if '--output-last-message' in sys.argv:
 pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(text)
else: print(text,end='')
''')
        script = self.wf / 'enhance.zsh'
        source = script.read_text().replace('/usr/bin/osascript', str(self.bin / 'osascript')).replace('/usr/bin/afplay', str(self.bin / 'afplay'))
        source = source.replace('script_path=', f'export PATH="{self.bin}:$PATH"\n\nscript_path=', 1)
        script.write_text(source)
        self.env = dict(os.environ, CLAUDE_BIN=str(self.cli), CODEX_BIN=str(self.cli),
                        ENHANCER_MODE='sonnet-5-5', alfred_workflow_cache=str(self.cache),
                        CLIP=str(self.clip), EVENTS=str(self.events), DELAYS=str(self.root/'delays'))

    def cleanup_fixture(self):
        # Final notification precedes the EXIT trap. Wait for terminal bookkeeping
        # and its lock release before removing files under detached workers.
        for gate in self.gates:
            gate.touch()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            jobs = list(self.cache.glob('job-*/request.md'))
            if all((p.parent/'completed').exists() for p in jobs): break
            time.sleep(.02)
        if (self.cache/'.lock').exists():
            subprocess.run(['/bin/zsh', '-c',
                'zmodload zsh/system; zsystem flock -t 10 -f fd "$1"',
                'fixture-cleanup', str(self.cache/'.lock')], check=True, timeout=12)
        self.tmp.cleanup()

    def write_bin(self, name, source):
        path = self.bin / name
        path.write_text(source)
        path.chmod(0o755)
        return path

    def wait(self, predicate):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(.02)
        self.fail('Timed out waiting for worker')

    def launch(self, text='selected text', **env):
        if 'GATE' in env: self.gates.append(Path(env['GATE']))
        return subprocess.run(['/bin/zsh', str(self.wf/'enhance.zsh'), text], cwd=self.root,
                              env=dict(self.env, **env), input='', text=True, capture_output=True, timeout=8)

    def finished(self):
        self.wait(lambda: self.events.exists() and any(x in self.events.read_text() for x in
                   ('|Prompt enhanced\n', '|Prompt enhancement failed\n', '|Prompt enhancement superseded\n')))

    def test_all_modes(self):
        for mode in ('opus-5-5','sonnet-5-5','haiku-5-5','fable-5-2','gpt-6.1-sol','gpt-6-luna','gpt-6-astra'):
            with self.subTest(mode=mode):
                self.events.unlink(missing_ok=True)
                self.assertEqual(self.launch(ENHANCER_MODE=mode).returncode, 0)
                self.finished()
                self.assertEqual(self.clip.read_text(), 'rewritten prompt')

    def test_busy_retry(self):
        self.launch(BEHAVIOR='busy')
        self.finished()
        self.assertTrue(self.clip.exists())
        self.assertEqual((self.root/'delays').read_text().split(), ['10','20'])

    def test_zero_status_busy_retry(self):
        self.launch(BEHAVIOR='busy-zero')
        self.finished()
        self.assertTrue(self.clip.exists())

    def test_retry_exhausted(self):
        self.launch(BEHAVIOR='busy', SUCCEED_AT='9')
        self.finished()
        self.assertFalse(self.clip.exists())
        self.assertEqual(next(self.cache.glob('job-*/attempts')).read_text(), '3')

    def test_failed_partial_is_not_copied(self):
        self.launch(BEHAVIOR='failed')
        self.finished()
        self.assertFalse(self.clip.exists())

    def test_blank_is_not_copied(self):
        self.launch(BEHAVIOR='blank')
        self.finished()
        self.assertFalse(self.clip.exists())

    def test_quoted_error_is_valid_output(self):
        self.launch(BEHAVIOR='quoted')
        self.finished()
        self.assertTrue(self.clip.exists())

    def test_auth_failure_rejected(self):
        result = self.launch(AUTH_FALSE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list(self.cache.glob('job-*')))

    def test_internal_flag_as_selected_text(self):
        self.assertEqual(self.launch('--run').returncode, 0)
        self.finished()
        self.assertTrue(self.clip.exists())

    def test_copy_failure_notifies(self):
        self.launch(COPY_FAIL='1')
        self.finished()
        self.assertIn('Prompt enhancement failed', self.events.read_text())

    def test_relative_cache(self):
        self.launch(alfred_workflow_cache='cache')
        self.finished()
        self.assertTrue(self.clip.exists())

    def test_running_jobs_survive_retention(self):
        gate = self.root/'active'
        self.launch(GATE=str(gate))
        self.wait(lambda: gate.with_suffix('.ready').exists())
        active = next(self.cache.glob('job-*'))
        os.utime(active, (1,1))
        for n in range(20):
            job = self.cache / f'job-20000102-{n}'
            job.mkdir()
            (job/'completed').touch()
        self.launch()
        self.finished()
        survived = active.exists()
        gate.touch()
        self.assertTrue(survived, 'cleanup deleted an active job')
        # The worker writes its marker, then prunes under the same lock, so
        # wait for both instead of counting in between.
        self.wait(lambda: (active/'completed').exists() and
                  len(list(self.cache.glob('job-*/completed'))) <= 20)

    def test_latest_accepted_job_owns_clipboard(self):
        older, newer = self.root/'older', self.root/'newer'
        self.launch(GATE=str(older), RESULT='older')
        self.wait(lambda: older.with_suffix('.ready').exists())
        self.launch(GATE=str(newer), RESULT='newer')
        self.wait(lambda: newer.with_suffix('.ready').exists())
        newer.touch()
        self.wait(lambda: self.clip.exists())
        older.touch()
        self.wait(lambda: len(list(self.cache.glob('job-*/output.txt'))) == 2 and
                  all(p.stat().st_size for p in self.cache.glob('job-*/output.txt')))
        self.wait(lambda: len(list(self.cache.glob('job-*/completed'))) == 2)
        self.assertEqual(self.clip.read_text(),'newer')

    def test_newer_failure_still_supersedes_older(self):
        gate = self.root/'older'
        self.launch(GATE=str(gate), RESULT='older')
        self.wait(lambda: gate.with_suffix('.ready').exists())
        self.launch(BEHAVIOR='failed')
        self.finished()
        gate.touch()
        self.wait(lambda: len(list(self.cache.glob('job-*/completed'))) == 2)
        self.assertFalse(self.clip.exists())

    def test_simultaneous_registration(self):
        gate = self.root/'batch'
        self.gates.append(gate)
        processes = [subprocess.Popen(['/bin/zsh', str(self.wf/'enhance.zsh'), str(n)],
                        cwd=self.root, env=dict(self.env, GATE=str(gate)),
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                     for n in range(6)]
        for proc in processes: self.assertEqual(proc.wait(timeout=8),0)
        gate.touch()
        self.wait(lambda: len(list(self.cache.glob('job-*/completed'))) == 6)
        states = [p.read_text().strip() for p in self.cache.glob('job-*/completed')]
        self.assertEqual(states.count('succeeded'),1)
        self.assertEqual(states.count('superseded'),5)

    def test_empty_output_for_both_providers(self):
        for mode in ('sonnet-5-5','gpt-6.1-sol'):
            self.events.unlink(missing_ok=True)
            self.launch(ENHANCER_MODE=mode, BEHAVIOR='empty')
            self.finished()
            self.assertFalse(self.clip.exists())

    def test_invalid_requests_do_not_create_jobs(self):
        self.assertNotEqual(self.launch(ENHANCER_MODE='unknown').returncode,0)
        self.assertNotEqual(self.launch('').returncode,0)
        self.assertFalse(list(self.cache.glob('job-*')))

    def test_custom_template_and_settings_are_snapshotted(self):
        custom = self.root/'custom'
        custom.mkdir()
        (custom/'sonnet-5-5.md').write_text('Custom instruction\n{{ABOUT_USER}}\n{{MISHEARD_NAMES}}\n')
        self.launch('literal $text', templates_dir=str(custom), about_you=' designer. ',
                    misheard_names=' Figma. ', effort='invalid')
        self.finished()
        job = next(self.cache.glob('job-*'))
        request = (job/'request.md').read_text()
        self.assertIn('Custom instruction',request)
        self.assertIn('About the user: designer.',request)
        self.assertIn('Names that often come through wrong include Figma.',request)
        self.assertIn('literal $text',request)
        self.assertIn('effort=medium',(job/'job.log').read_text())

    def test_relative_cli_override(self):
        self.assertEqual(self.launch(CLAUDE_BIN='bin/model').returncode,0)
        self.finished()
        self.assertTrue(self.clip.exists())

    def build(self):
        shutil.copy2(ROOT/'build.sh', self.root/'build.sh')
        return subprocess.run(['/bin/zsh', str(self.root/'build.sh')], capture_output=True, text=True)

    def test_build_rejects_missing_action(self):
        path = self.wf/'info.plist'
        data = plistlib.loads(path.read_bytes())
        data['objects'] = [o for o in data['objects'] if
            o['config'].get('variables',{}).get('ENHANCER_MODE') != 'sonnet-5-5']
        path.write_bytes(plistlib.dumps(data))
        self.assertNotEqual(self.build().returncode,0)

    def test_build_rejects_orphan_template(self):
        (self.wf/'templates'/'unknown.md').write_text('template')
        self.assertNotEqual(self.build().returncode,0)


if __name__ == '__main__': unittest.main()
