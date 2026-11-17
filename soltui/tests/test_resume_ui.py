"""Task-1541 UI regressions; transports and all filesystem state are disposable."""
from __future__ import annotations

import csv
import fcntl
import io
import json
import os
import shlex
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from soltui import app as menubar
from soltui import (
    bots_screens,
    config,
    csv_table,
    docs_browser,
    experiment_screens,
    live_tools,
    native_host_install,
    shell,
)
from soltui.tests.bridge_support import World
from soltui.tests.test_tui import make_settings
from soltui.tui import SolTuiApp


class Widget:
    def __init__(self, value=""):
        self.value = value
        self.disabled = False
        self.text = ""
        self.rows = []
    def update(self, value): self.text = str(value)
    def clear(self): self.rows.clear()
    def add_row(self, *args, **kwargs): self.rows.append((args, kwargs))


class ResumeUI(unittest.TestCase):
    def setUp(self):
        self.world = self.enterContext(World())

    def menu(self, settings=None):
        class FakeApp:
            def __init__(self, **kwargs): self.menu = {}
        rumps = NS(App=FakeApp, Timer=lambda *a: NS(start=lambda: None), clicked=lambda *a: lambda f: f,
                   notification=mock.Mock())
        self.enterContext(mock.patch.object(menubar, '_rumps', return_value=rumps))
        self.enterContext(mock.patch.object(menubar.serve_mod, 'find_port', return_value=None))
        return menubar.build_app(settings or make_settings()), rumps

    def test_CDO_60bfba4c36_saved_menubar_roster(self):
        settings = make_settings()
        settings.roster = [{'name': 'ma_crossover', 'params': {'fast': 9, 'slow': 40}}]
        app, _ = self.menu(settings)
        self.assertEqual(app.roster.to_list(), settings.roster)
        with mock.patch.object(app.runner, 'start') as start:
            app.run_backtest(None)
        self.assertEqual(start.call_args.args[0].to_list(), settings.roster)

    def test_CDO_60bfba4c36_empty_and_legacy_rosters_match_console_contract(self):
        from soltui import commands
        for names in ([],['rsi']):
            settings=make_settings(); settings.roster=[]; settings.enabled_strategies=names
            app,_=self.menu(settings)
            expected=commands.Context.from_settings(settings,commands.Runtime()).roster
            self.assertEqual(app.roster.to_list(),expected.to_list())
            if not names: self.assertEqual(len(app.roster),0)

    def test_CDO_2a3deb9cc1_stderr_is_continuously_drained_and_bounded(self):
        capture = menubar._ConsoleErrors(io.BytesIO(b'x' * 100_000 + b'\nfixture diagnostic\x00'))
        capture.thread.join(2)
        self.assertFalse(capture.thread.is_alive())
        self.assertLessEqual(len(capture.tail), capture.limit)
        self.assertIn('fixture diagnostic', capture.message())
        self.assertNotIn('\x00', capture.message())

    def test_CDO_8d2cfadeaf_timeout_cleans_only_owned_child_before_retry(self):
        app, rumps = self.menu()
        child = mock.Mock(stderr=io.BytesIO(b'fixture startup failure'))
        child.poll.return_value = None
        with mock.patch.object(menubar.serve_mod, 'find_port', return_value=8899), \
             mock.patch.object(menubar.subprocess, 'Popen', return_value=child) as spawn, \
             mock.patch.object(menubar, '_wait_for_port', return_value=False), \
             mock.patch.object(menubar.webbrowser, 'open') as browser:
            app.open_console(None)
            self.assertIsNone(app.serve_proc)
            child.terminate.assert_called_once()
            child.wait.assert_called()
            app.open_console(None)
        self.assertEqual(spawn.call_count, 2)
        browser.assert_not_called()
        self.assertTrue(rumps.notification.called)

    def test_CDO_2945767f45_terminal_has_two_independent_quote_boundaries(self):
        app, _ = self.menu()
        repo = Path('/fixture/has space/quote" and \' $(touch nope)')
        python = '/fixture/Python App/"python"\\bin'
        with mock.patch.object(menubar, 'REPO', repo), mock.patch.object(menubar.sys, 'executable', python), \
             mock.patch.object(menubar.subprocess, 'run', return_value=NS(returncode=0)) as run:
            app.open_tui(None)
        script = run.call_args.args[0][-1]
        # JSON string escaping is a compatible AppleScript string boundary here.
        command = json.loads(script.split('do script ', 1)[1])
        self.assertEqual(shlex.split(command), ['cd', str(repo), '&&', python, '-m', 'soltui.tui'])

    def test_CDO_edd779140f_equal_count_candidate_identity(self):
        widgets = {k: Widget() for k in ('#opt-head', '#opt-progress', '#opt-candidates')}
        progress = {'run': 'one', 'candidates': [{'index': 1, 'changes': {'coin': 'SOL'}}]}
        screen = bots_screens.OptimizeScreen('fixture', lambda: progress)
        with mock.patch.object(screen, 'query_one', side_effect=lambda key, *a: widgets[key]):
            screen.refresh_progress()
            progress['candidates'] = [{'index': 1, 'changes': {'coin': 'ETH'}}]
            screen.refresh_progress()
        self.assertIn('ETH', str(widgets['#opt-candidates'].rows))
        self.assertNotIn('SOL', str(widgets['#opt-candidates'].rows))

    def test_CDO_703af5826a_growing_documents_are_bounded_before_decode_or_save(self):
        stream = io.BytesIO(b'a' * (docs_browser.MAX_VIEW_BYTES + 20))
        target = mock.Mock()
        target.stat.return_value.st_size = 1
        target.open.return_value.__enter__ = mock.Mock(return_value=stream)
        target.open.return_value.__exit__ = mock.Mock(return_value=False)
        with mock.patch.object(docs_browser, 'resolve', return_value=target):
            result = docs_browser.read_document('one.md', [])
        self.assertFalse(result[2])
        self.assertIn('limit', result[0])
        self.assertEqual(stream.tell(), docs_browser.MAX_VIEW_BYTES + 1)
        # The shared bounded reader also guards write_document's revision read.
        with mock.patch.object(Path, 'open', return_value=io.BytesIO(b'a' * (docs_browser.MAX_VIEW_BYTES + 20))), self.assertRaisesRegex(ValueError, 'limit'):
            docs_browser._read_bounded(Path('fixture'))

    def test_CDO_cc895aed1d_csv_formula_prefixes_headers_and_values(self):
        labels = ['=SUM(1)', '+SUM(1)', '-1+2', '@SUM(1)', '\tformula', '\rformula', '\nformula', '  =1+1', '\x00=1+1', 'symbol']
        table = NS(id='fixture', ordered_columns=[NS(label=x) for x in labels], row_count=1,
                   get_row_at=lambda _: labels[:-1] + ['=remote-token'])
        with tempfile.TemporaryDirectory() as directory:
            first = csv_table.export_table(table, Path(directory)); second = csv_table.export_table(table, Path(directory))
            self.assertNotEqual(first, second)
            with first.open(newline='') as handle: rows = list(csv.reader(handle))
        self.assertTrue(all(x.startswith("'") for x in rows[0][:-1]))
        self.assertEqual(rows[0][-1], 'symbol')
        self.assertTrue(all(x.startswith("'") for x in rows[1]))
        self.assertEqual(csv_table._spreadsheet_cell(-12.5), '-12.5')
        self.assertEqual(csv_table._spreadsheet_cell('-12.5'), '-12.5')

    def experiment(self):
        screen = experiment_screens.ExperimentScreen('grid', lambda *a: {})
        widgets = {k: Widget() for k in ('#exp-adopt', '#exp-resume', '#exp-pause', '#exp-cancel', '#exp-final', '#exp-run-detail', '#exp-candidate-detail', '#exp-cell-detail', '#exp-candidate-table', '#exp-cell-table')}
        screen.query_one = lambda key, *a: widgets[key]
        screen._input = lambda key: ''
        screen._selected = lambda key: ''
        screen.run_id = 'A'; screen.run = {'id':'A', 'spec':{}, 'status':'paused'}
        return screen, widgets

    def test_CDO_c775891553_selected_run_never_retargets_old_consent(self):
        screen, widgets = self.experiment(); widgets['#exp-adopt'].value = True
        with mock.patch.object(screen, '_command') as command:
            screen.selected_run(NS(row_key=NS(value='B')))
            for action in ('start', 'pause', 'cancel', 'finalize'): screen._control(action)
        self.assertEqual([x.args[0] for x in command.call_args_list], ['experiments.get'])
        self.assertFalse(widgets['#exp-adopt'].value)
        self.assertTrue(all(widgets[f'#exp-{name}'].disabled for name in ('resume','pause','cancel','final')))
        self.assertEqual(screen.run, {})
        with mock.patch.object(screen, '_command') as command:
            screen._loaded_run({'id':'B','spec':{'source':'native'},'status':'paused','worker_active':False})
            for action in ('start','pause','cancel','finalize'): screen._control(action)
        mutations=[call for call in command.call_args_list if call.args[0] in ('experiments.start','experiments.pause','experiments.cancel','experiments.finalize')]
        self.assertEqual(len(mutations),4)
        self.assertTrue(all(call.args[1]['run_id']=='B' for call in mutations))
        self.assertFalse(mutations[-1].args[1]['adopt'])

    def test_CDO_e387f02bff_only_newest_same_run_evidence_can_publish(self):
        screen, _ = self.experiment(); callbacks=[]; accepts=[]
        def command(name,params,callback,**kw): callbacks.append(callback); accepts.append(kw['accept'])
        screen._command = command
        screen._cells_loaded = mock.Mock()
        screen.selected_candidate = 'A'; screen.filter_cells()
        screen.selected_candidate = 'B'; screen.filter_cells()
        callbacks[1](['B']); callbacks[0](['A'])
        self.assertEqual(screen._cells_loaded.call_args_list, [mock.call(['B'])])
        status=Widget(); receiver=NS(_workbench_closed=False,is_attached=True,_polling=False,query_one=lambda *a:status)
        error={'ok':False,'error':{'message':'visible current failure'}}
        experiment_screens.ExperimentScreen._received(receiver,'experiments.cells',error,None,True,accepts[0])
        self.assertEqual(status.text,'')
        experiment_screens.ExperimentScreen._received(receiver,'experiments.cells',error,None,True,accepts[1])
        self.assertIn('visible current failure',status.text)

    def test_CDO_41c6b3664e_previews_cannot_crowd_submitted_local_actions(self):
        from soltui import coinbase_manual, jupiter_manual
        directory = self.world.root / 'journal'; directory.mkdir()
        for i in range(15):
            path=directory/f'{i:02}.json'; path.write_text(json.dumps({'submit_started_at': 123.} if i==0 else {})); os.utime(path,(i+100,i+100))
        with mock.patch.object(coinbase_manual, '_dir', return_value=directory), mock.patch.object(jupiter_manual, '_storage_dir', return_value=directory/'absent'):
            rows=live_tools._local_actions(1)
        self.assertEqual(len(rows),1); self.assertEqual(rows[0]['at'],123.)

    def test_CDO_18d542ae08_running_recorder_without_finite_age_is_unavailable(self):
        for age in (None,-1,float('nan'),float('inf')):
            reads={'prices.status':{'ok':True,'result':{'running':True,'snapshot_age_s':age}}}
            health=next(h for h in shell.health_items(reads) if h.label=='Prices')
            self.assertEqual(health.kind,'warn')
            self.assertTrue(any('Price' in n.title and n.kind=='warn' for n in shell.needs(reads)))

    def test_CDO_694682457e_native_host_paths_resolve_at_invocation_directory(self):
        with mock.patch.object(native_host_install, 'browser_host_dirs', return_value=[]):
            old=os.getcwd()
            try:
                os.chdir(self.world.root)
                result=native_host_install.install(repo=Path('.'), python=Path('venv/bin/python'), wrapper=Path('wrapper'), dirs=[Path('hosts')])
                manifest=json.loads(Path(result['manifests'][0]).read_text())
            finally: os.chdir(old)
        self.assertTrue(Path(result['python']).is_absolute()); self.assertTrue(Path(manifest['path']).is_absolute())
        self.assertIn(shlex.quote(str(self.world.root/'venv/bin/python')), Path(result['wrapper']).read_text())
        system=self.world.root/'python-system'; system.write_text('inert interpreter fixture')
        interpreter=self.world.root/'venv/bin/python'; interpreter.parent.mkdir(parents=True); interpreter.symlink_to(system)
        result=native_host_install.install(repo=self.world.root,python=interpreter,wrapper=self.world.root/'wrapper',dirs=[self.world.root/'hosts'])
        self.assertEqual(result['python'],str(interpreter))
        self.assertIn(str(interpreter),Path(result['wrapper']).read_text())

    def test_CDO_2de6e8be04_hyperliquid_form_roundtrip_and_CDO_179b259497_mint_identity(self):
        from textual.widgets import Checkbox
        mint='AbCdEfGhijkLMNopQRsTuvWXyz123456789abcdefgh'
        widgets={'#set-hyperliquid_address':Widget('0x'+'12'*20), '#set-interval':Widget('1m'),
                 '#advanced-venue':Widget('jupiter'), '#advanced-type':Widget('market'), '#advanced-side':Widget('BUY'),
                 '#advanced-product':Widget(mint), '#advanced-size':Widget('10'), '#advanced-unit':Widget('quote')}
        def query(key, cls=None): return widgets.get(key, Widget(False if cls is Checkbox else ''))
        fake=NS(query_one=query, query=lambda key: [])
        patch=SolTuiApp._read_form(fake)
        self.assertEqual(patch['hyperliquid_address'],'0x'+'12'*20)
        from soltui import commands
        ctx=commands.Context.from_settings(make_settings(),commands.Runtime())
        saved=commands.dispatch('settings.save',{'hyperliquid_address':patch['hyperliquid_address']},ctx=ctx,quiet=True)
        self.assertTrue(saved['ok'],saved)
        self.assertEqual(config.load_settings().hyperliquid_address,patch['hyperliquid_address'])
        self.assertEqual(SolTuiApp._advanced_values(fake)[3],mint)
        widgets['#advanced-leverage']=Widget('1x'); widgets['#advanced-position']=Widget('long')
        fake._advanced_values=lambda:SolTuiApp._advanced_values(fake)
        fake._advanced_signature=lambda:SolTuiApp._advanced_signature(fake)
        fake._advanced_supported=lambda:SolTuiApp._advanced_supported(fake)
        fake._coinbase_order_busy=False; fake._coinbase_order_unknown=False
        fake._coinbase_order_controls=lambda:None; fake._advanced_generation=0; fake._advanced_worker=mock.Mock()
        SolTuiApp._advanced_preview_pressed(fake)
        self.assertEqual(fake._advanced_worker.call_args.args[0],'jupiter.order_preview')
        self.assertEqual(fake._advanced_worker.call_args.args[1]['product_id'],mint)
        widgets['#advanced-venue'].value='coinbase'; widgets['#advanced-product'].value='sol-usd'
        self.assertEqual(SolTuiApp._advanced_values(fake)[3],'SOL-USD')

    def test_CDO_25ccdb3214_passive_same_and_different_document_opens_keep_draft(self):
        view=NS(text='unsaved'); status=Widget()
        fake=NS(query=lambda key: True, query_one=lambda key,*a: view if key=='#docs-view' else status,
                _docs_current_path='same.md',_docs_loaded_text='disk',_call=mock.Mock(side_effect=AssertionError('passive dirty read')))
        for path in ('same.md','different.md'): SolTuiApp._open_doc(fake,path)
        self.assertEqual(view.text,'unsaved'); fake._call.assert_not_called()
        fake._call=mock.Mock(return_value={'ok':True,'result':{'text':'disk original','language':'','editable':True,'revision':'0'*64}})
        SolTuiApp._open_doc(fake,'same.md',force=True)
        self.assertEqual(view.text,'disk original'); self.assertEqual(fake._docs_loaded_text,'disk original')
        self.assertIn('discarded unsaved edit',status.text)

    def test_CDO_9ca0b6a3b6_sorted_detail_identity_uses_record_keys(self):
        a,b={'label':'A'},{'label':'B'}
        fake=NS(_on_compound_tab=lambda:True,_compound_coin='SOL',_compound_result_rows=[a,b],_show_preview=mock.Mock())
        with mock.patch('soltui.tui.compound_mod.record_preview',side_effect=lambda title,row,*a:row):
            SolTuiApp._compound_result_highlighted(fake, NS(cursor_row=0,row_key=NS(value='B')))
        self.assertIs(fake._show_preview.call_args.args[1],b)
        fake._compound_forward_rows=[{'bar_ts':1},{'bar_ts':2}]
        with mock.patch('soltui.tui.compound_mod.record_preview',side_effect=lambda title,row,*a:row):
            SolTuiApp._compound_forward_highlighted(fake,NS(cursor_row=0,row_key=NS(value='2')))
        self.assertEqual(fake._show_preview.call_args.args[1]['bar_ts'],2)
        fake._signal_live_prediction_rows=[a,b]; fake._signal_live_show_detail=mock.Mock()
        SolTuiApp._signal_live_row_highlighted(fake,NS(cursor_row=0,row_key=NS(value='B')))
        fake._signal_live_show_detail.assert_called_once_with(1)

    def test_CDO_eb31dcd5a0_icon_staging_never_deletes_existing_sibling(self):
        from soltui import make_icon
        target=self.world.root/'fixture.icns'; sibling=target.with_suffix('.iconset'); sibling.mkdir()
        sentinel=sibling/'owner.txt'; sentinel.write_text('preserve')
        image=mock.Mock(); image.resize.return_value=image
        def iconutil(args,**kw):
            staging=Path(args[3]); self.assertNotEqual(staging,sibling)
            self.assertTrue(staging.is_dir()); self.assertEqual(staging.suffix,'.iconset')
            return NS(returncode=1,stderr='fixture failure')
        with mock.patch.object(make_icon.shutil,'which',return_value='/fixture/iconutil'), \
             mock.patch.object(make_icon,'render',return_value=image), \
             mock.patch.object(make_icon.subprocess,'run',side_effect=iconutil), self.assertRaisesRegex(RuntimeError,r'iconutil conversion failed \(exit 1\)'):
            make_icon.build_icns(target)
        self.assertEqual(sentinel.read_text(),'preserve')
        self.assertEqual(list(self.world.root.glob('soltui-*.iconset')),[])

    def test_CDO_a691799882_idle_exit_hands_refresh_to_a_new_owner(self):
        directory=live_tools.root(); directory.mkdir(parents=True)
        handle=(directory/'worker.lock').open('a+b'); fcntl.flock(handle,fcntl.LOCK_EX)
        fd=os.dup(handle.fileno()); handle.close()
        live_tools.write(directory/'worker.json',{'token':'fixture-owner'})
        live_tools.write(directory/'requests.json',{})
        read=live_tools.read; results=[]; admitted=threading.Event(); worker=[]
        def refresh():
            admitted.set(); results.append(live_tools.refresh('SOL'))
        def intercept(path,default=None):
            value=read(path,default)
            if path.name=='requests.json' and not worker:
                if live_tools.locked(directory/'control.lock'):
                    thread=threading.Thread(target=refresh); worker.append(thread); thread.start()
                    self.assertTrue(admitted.wait(2))
                else:
                    # Old code acknowledged a refresh against the still-held
                    # worker lease after already taking an empty idle snapshot.
                    worker.append(None); refresh()
            return value
        fake_child=NS(wait=lambda:0)
        with mock.patch.object(live_tools,'read',side_effect=intercept), \
             mock.patch.object(live_tools.signal,'signal'), \
             mock.patch.object(live_tools.subprocess,'Popen',return_value=fake_child) as spawn:
            self.assertEqual(live_tools.main(['--lock-fd',str(fd),'--token','fixture-owner']),0)
            for thread in worker:
                if thread: thread.join(3); self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]['state'],'starting')
        spawn.assert_called_once()
        self.assertEqual(read(directory/'worker.json')['state'],'starting')
        self.assertIn('SOL',read(directory/'requests.json'))

    def test_CDO_1cb6d57960_signal_save_reset_leave_inherited_config_bytes_untouched(self):
        from soltui import commands
        outer=(config.CONFIG_PATH,config.CONFIG_PATH_JSON)
        for path in outer: path.parent.mkdir(parents=True,exist_ok=True); path.write_text('sentinel owner bytes')
        with World() as world:
            ctx=commands.Context.from_settings(make_settings(),commands.Runtime())
            for name,params in [('signals.save',{'values':{'rsi_period':9}}),('signals.reset',{})]:
                result=commands.dispatch(name,params,ctx=ctx,quiet=True)
                self.assertTrue(result['ok'],result)
                self.assertTrue(config.CONFIG_PATH.is_relative_to(world.root))
                self.assertTrue(config.CONFIG_PATH_JSON.is_relative_to(world.root))
                self.assertTrue(config.CONFIG_PATH.exists() or config.CONFIG_PATH_JSON.exists())
            self.assertNotEqual(config.CONFIG_PATH,outer[0]); self.assertNotEqual(config.CONFIG_PATH_JSON,outer[1])
        self.assertEqual((config.CONFIG_PATH,config.CONFIG_PATH_JSON),outer)
        self.assertTrue(all(p.read_text()=='sentinel owner bytes' for p in outer))

    def test_CDO_8d2cfadeaf_ready_child_reuses_only_after_readiness_check(self):
        app,_=self.menu(); child=mock.Mock(stderr=io.BytesIO(b'fixture startup'))
        child.poll.return_value=None
        with mock.patch.object(menubar.serve_mod,'find_port',return_value=8899), \
             mock.patch.object(menubar.subprocess,'Popen',return_value=child) as spawn, \
             mock.patch.object(menubar,'_wait_for_port',return_value=True) as ready, \
             mock.patch.object(menubar.webbrowser,'open') as browser:
            app.open_console(None); app.open_console(None)
        self.assertEqual(spawn.call_count,1); self.assertEqual(ready.call_count,2); self.assertEqual(browser.call_count,2)
        self.assertIs(app.serve_proc,child)

    def test_CDO_703af5826a_save_reads_only_limit_plus_one_even_after_growth(self):
        directory=self.world.root/'docs'; directory.mkdir(); path=directory/'one.md'; path.write_text('a')
        lock_root=self.world.root/'fixture-lock-root'; lock_root.mkdir()
        def task_path(*args,**kwargs): return lock_root if args==('/tmp',) else Path(*args,**kwargs)
        entry=docs_browser.DocEntry('one.md','one.md','','doc','','none',1,1)
        sizes=[]
        class Stream(io.BytesIO):
            def read(self,size=-1): sizes.append(size); return super().read(size)
        original=Path.open
        def opened(target,*args,**kwargs):
            if target.resolve()==path.resolve() and args==('rb',): return Stream(b'a'*(docs_browser.MAX_VIEW_BYTES+20))
            return original(target,*args,**kwargs)
        with mock.patch.object(docs_browser,'REPO',directory), mock.patch.object(docs_browser,'Path',new=task_path), mock.patch.object(Path,'open',new=opened), self.assertRaisesRegex(ValueError,'limit'):
            docs_browser.write_document('one.md','changed',[entry],expected_revision=docs_browser.document_revision('a'))
        self.assertEqual(sizes,[docs_browser.MAX_VIEW_BYTES+1]); self.assertEqual(path.read_text(),'a')

    def test_CDO_8d2cfadeaf_unreaped_child_keeps_ownership_and_blocks_duplicate(self):
        app,_=self.menu(); child=mock.Mock(stderr=io.BytesIO(b'fixture'))
        child.poll.return_value=None
        app.serve_proc=child; app.serve_port=8899
        child.wait.side_effect=menubar.subprocess.TimeoutExpired('fixture',2)
        with mock.patch.object(menubar,'_wait_for_port',return_value=False), mock.patch.object(menubar.subprocess,'Popen') as spawn:
            app.open_console(None)
        self.assertIs(app.serve_proc,child); spawn.assert_not_called()


    def test_CDO_2a3deb9cc1_long_lived_child_drains_real_bounded_pipe(self):
        app,_=self.menu(); reader,writer=os.pipe(); complete=threading.Event(); close=threading.Event()
        child=mock.Mock(stderr=os.fdopen(reader,'rb')); child.poll.return_value=None
        def noisy_child():
            try:
                payload=b'fixture error tail\n'*10000
                while payload:
                    count=os.write(writer,payload); payload=payload[count:]
                complete.set(); close.wait(5)
            finally: os.close(writer)
        producer=threading.Thread(target=noisy_child,daemon=True); producer.start()
        def ready(*a,**kw):
            self.assertTrue(complete.wait(2),'stderr producer filled the pipe while child was still alive')
            return True
        try:
            with mock.patch.object(menubar.serve_mod,'find_port',return_value=8899), \
                 mock.patch.object(menubar.subprocess,'Popen',return_value=child), \
                 mock.patch.object(menubar,'_wait_for_port',side_effect=ready), \
                 mock.patch.object(menubar.webbrowser,'open'):
                app.open_console(None)
            self.assertIsNone(child.poll()); self.assertLessEqual(len(app.serve_errors.tail),app.serve_errors.limit)
            self.assertIn('fixture error tail',app.serve_errors.message())
        finally:
            close.set(); producer.join(3)
            if app.serve_errors: app.serve_errors.thread.join(3)


    def test_verify_detached_tab_activation_cannot_touch_removed_widgets_or_dispatch(self):
        for running, pane in (
            (True, NS(id='tab-forwardtest', is_attached=False)),
            (False, NS(id='tab-forwardtest', is_attached=True)),
            (True, None),
        ):
            with self.subTest(running=running, pane=pane):
                fake=NS(is_running=running,_forward_refresh=mock.Mock())
                SolTuiApp._populate_on_first_view(fake,NS(pane=pane))
                fake._forward_refresh.assert_not_called()


class MountedRecordIdentity(unittest.IsolatedAsyncioTestCase):
    async def test_CDO_9ca0b6a3b6_real_table_sort_resolves_original_record_keys(self):
        from textual.app import App
        from textual.widgets import DataTable
        class Harness(App):
            def compose(self):
                yield DataTable(id='compound-results')
                yield DataTable(id='compound-forward-table')
                yield DataTable(id='signal-live-predictions-table')
        rows=[]
        for label in ('A','B'):
            rows.append({"label": label,"oos_return": 0.,"oos_sharpe": 0.,"oos_trades": 0,"oos_fees_pct": 0.,"oos_calls": 0,
                             "oos_hit": 0.,"oos_z": 0.,"oos_gross_bps": 0.,"oos_max_dd": 0.,"ranked": False})
        recent=[{"bar_ts": t,"call": str(t),"composite": 0.,"regime": 'fixture',"price": 1.,"ret_bps": None,"hit": None} for t in (60,120)]
        tally={"decided": 0,"hit_rate": None,"z_vs_coinflip": None,"net_bps_per_call_if_one_bar": None}
        response={'compound.results':{"rows": rows,"run_id": None}, 'compound.forward_status':{"asset": 'SOL',"components": {},
            "compound": tally,"compound_ungated": tally,"calls_recorded": 2,"resolved": 0,"pending": 2,"recent": recent}}
        with World():
            async with Harness().run_test() as pilot:
                app=pilot.app; tables={key:app.query_one('#'+key,DataTable) for key in ('compound-results','compound-forward-table','signal-live-predictions-table')}
                for key,count in (('compound-results',14),('compound-forward-table',8),('signal-live-predictions-table',1)):
                    tables[key].add_columns(*(str(i) for i in range(count)))
                fake=NS(_compound_coin='SOL',_compound_cfg={},_on_compound_tab=lambda:True,_show_preview=mock.Mock(),
                        _compound_render_table=mock.Mock(),_msg=lambda env:'fixture',
                        _call=lambda name,*a,**kw:{"ok": True,"result": response[name]},
                        query_one=lambda key,*a:tables.get(key[1:],Widget()))
                with mock.patch('soltui.tui.compound_mod.run_summary',return_value='fixture'), \
                     mock.patch('soltui.tui.compound_mod.tested_line',return_value='fixture'):
                    SolTuiApp._compound_load_results(fake)
                predictions=tables['signal-live-predictions-table']
                predictions.add_row('A',key='A'); predictions.add_row('B',key='B')
                fake._signal_live_prediction_rows=[{'label':'A'},{'label':'B'}]; fake._signal_live_show_detail=mock.Mock()
                with mock.patch('soltui.tui.compound_mod.record_preview',side_effect=lambda title,row,*a:row):
                    for reverse in (False,True):
                        for key,handler in [('compound-results',SolTuiApp._compound_result_highlighted),('compound-forward-table',SolTuiApp._compound_forward_highlighted),('signal-live-predictions-table',SolTuiApp._signal_live_row_highlighted)]:
                            table=tables[key]; table.sort(table.ordered_columns[0].key,reverse=reverse)
                            for position,shown in enumerate(table.ordered_rows):
                                handler(fake,NS(cursor_row=position,row_key=shown.key))
                                if key=='compound-results': self.assertEqual(fake._show_preview.call_args.args[1]['label'],shown.key.value)
                                elif key=='compound-forward-table': self.assertEqual(str(fake._show_preview.call_args.args[1]['bar_ts']),shown.key.value)
                                else: self.assertEqual(fake._signal_live_prediction_rows[fake._signal_live_show_detail.call_args.args[0]]['label'],shown.key.value)
