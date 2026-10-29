import importlib.util, pathlib

ROOT = pathlib.Path(__file__).parents[2]
def load(path, name):
    spec=importlib.util.spec_from_file_location(name, path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_state_machine():
    m=load(ROOT/'device/android-diagnostic-device/core/device.py','device_core')
    sm=m.DeviceStateMachine(); sm.transition(m.DeviceMode.DIAGNOSTIC)
    assert sm.mode == m.DeviceMode.DIAGNOSTIC
    try: sm.transition(m.DeviceMode.DIAGNOSTIC)
    except ValueError: pass
    else: raise AssertionError('invalid transition accepted')

def test_local_store_and_sync_queue():
    m=load(ROOT/'device/android-diagnostic-device/storage/local_store.py','store')
    qmod=load(ROOT/'device/android-diagnostic-device/sync/queue.py','queue')
    s=m.LocalDiagnosticStore()
    try:
        s.upsert('s1','session',{'status':'created'},1.0)
        assert s.get('s1')['payload']['status']=='created'
        q=qmod.SyncQueue(s.db); op=q.enqueue('session.upsert',{'id':'s1'}); assert len(q.pending())==1
        q.acknowledge(op.id); assert q.pending()==[]
    finally:
        s.close()

def test_vci_codec_roundtrip():
    m=load(ROOT/'device/android-diagnostic-device/transport/custom_vci.py','vci')
    packet=m.VciPacket(1,b'abc'); assert m.CustomVciCodec.decode(m.CustomVciCodec.encode(packet)) == packet

def test_ota_policy():
    m=load(ROOT/'device/android-diagnostic-device/ota/manifest.py','ota')
    good=m.OtaManifest('1.2.0','https://example.invalid/update.bin','a'*64,'1.0.0')
    m.OtaPolicy.validate(good)

def test_health():
    m=load(ROOT/'device/android-diagnostic-device/health/monitor.py','health')
    h=m.HealthMonitor().evaluate(90,40,5000,'wifi'); assert h.level == m.HealthLevel.OK
