import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from obd.catalog import reference_vehicles, selector_entries, compatibility
from catalog_sources.wikimedia import image_metadata


def test_reference_engines_are_real_named_options_without_fitment_claims():
    cars = reference_vehicles()
    assert len(cars) == 70
    assert sum(len(c['engines']) for c in cars) == 199
    assert len({c['id'] for c in cars}) == len(cars)
    assert all(c['source_url'].startswith('https://en.wikipedia.org/wiki/') for c in cars)
    assert all(c['protocol_policy'] == 'auto_detect_on_vehicle' for c in cars)
    assert all(e['fitment_status'] == 'generation_reference_not_year_or_market_verified' for c in cars for e in c['engines'])
    assert any(c['model'] == 'Prius' and c['engines'][0]['type'] == 'hybrid' for c in cars)


def test_reference_filtering_and_unverified_fitment_scope():
    entries = selector_entries(make='Toyota',model='Prius',year=2011)
    assert entries and all(c['year'] == 2011 and c['model'] == 'Prius' for c in entries)
    assert all(c['ecu'] is None and not c['fitment_verified'] for c in entries)
    assert selector_entries(make='Toyota',model='Prius',year=1900) == []


def test_models_never_become_observed_protocols():
    known = compatibility('Toyota','Prius',2011,None,'US')
    assert known['references'] and known['status'] == 'requires_adapter_detection'
    assert known['observed_protocol'] is None and not known['confirmed_fitment']
    assert not known['all_vehicles_supported']
    unknown = compatibility('Unknown','Unknown',2000,None,None)
    assert unknown['references'] == [] and unknown['protocol_id'] == 'auto'


def fake_wiki(license_name='CC BY-SA 4.0',image_url='https://upload.wikimedia.org/car.jpg'):
    def get(host, **params):
        if host == 'en.wikipedia.org':return {'query':{'pages':[{'pageimage':'Car.jpg'}]}}
        return {'query':{'pages':[{'imageinfo':[{'url':image_url,'descriptionurl':'https://commons.wikimedia.org/wiki/File:Car.jpg',
           'extmetadata':{'LicenseShortName':{'value':license_name},'Artist':{'value':'<b>Photographer</b>'},
                          'LicenseUrl':{'value':'https://creativecommons.org/licenses/by-sa/4.0/'}}}]}]}}
    return get


def test_wikimedia_retains_source_creator_and_license():
    metadata = image_metadata('Toyota Prius (XW30)',get=fake_wiki())
    assert metadata['creator'] == 'Photographer'
    assert metadata['license'] == 'CC BY-SA 4.0'
    assert metadata['source_page'].startswith('https://commons.wikimedia.org/')


@pytest.mark.parametrize('license_name',['','Fair use','All rights reserved'])
def test_no_unlicensed_or_fair_use_images_imported(license_name):
    with pytest.raises(ValueError):image_metadata('Car',get=fake_wiki(license_name))


def test_wikimedia_download_url_is_restricted():
    with pytest.raises(ValueError):image_metadata('Car',get=fake_wiki(image_url='http://127.0.0.1/private'))


def test_reference_api_images_and_catalog_survive_unavailable_database(monkeypatch):
    import api.main as main
    import api.vehicle_catalog_routes as catalog
    from fastapi import HTTPException
    def offline(*args):raise HTTPException(503,'database offline')
    monkeypatch.setattr(catalog,'_run_all',offline)
    with TestClient(main.app) as client:
        assert len(client.get('/api/v1/vehicle-reference').json()['vehicles']) == 70
        entries = client.get('/api/v1/vehicle-catalog/entries?make=Toyota&model=Prius').json()
        assert entries and all(e['scope']=='generation-reference-not-vin-fitment' for e in entries)
        assert 'Nissan' in client.get('/api/v1/vehicle-catalog/makes').json()
        assert client.get('/api/v1/vehicle-reference/toyota_corolla_e140-e150/image').headers['content-type'] == 'image/png'
        assert client.get('/api/v1/vehicle-reference/unknown/image').status_code == 404
        assert client.get('/api/v1/vehicle-reference/nissan_qashqai_j10/image').status_code == 200


def test_reference_image_manifest_cannot_serve_arbitrary_files(monkeypatch,tmp_path):
    import api.vehicle_reference_routes as routes
    monkeypatch.setattr(routes,'project_root',lambda:tmp_path)
    monkeypatch.setattr(routes,'reference_vehicles',lambda:[{'id':'car','image':{'path':'../../etc/passwd'}}])
    with pytest.raises(Exception) as error:routes.image('car')
    assert error.value.status_code == 404


def test_wikimedia_import_writes_photo_and_attribution_atomically(monkeypatch,tmp_path):
    import importlib.util
    from io import BytesIO
    from PIL import Image
    path = Path(__file__).resolve().parents[2] / 'scripts/import_wikimedia_vehicles.py'
    spec = importlib.util.spec_from_file_location('import_wikimedia_for_test',path)
    importer = importlib.util.module_from_spec(spec); spec.loader.exec_module(importer)
    (tmp_path/'data').mkdir()
    (tmp_path/'data/vehicle_reference.json').write_text(json.dumps({'vehicles':[{'id':'toyota_test','make':'Toyota','wikipedia_title':'Toyota'}]}))
    content = BytesIO(); Image.new('RGB',(30,20),'red').save(content,format='PNG')
    monkeypatch.setattr(importer,'ROOT',tmp_path)
    monkeypatch.setattr(importer,'image_metadata',lambda title:{'license':'CC BY-SA 4.0','creator':'Author','download_url':'https://upload.wikimedia.org/image.png','source_page':'https://commons.wikimedia.org/wiki/File:Image.png','kind':'wikimedia_commons'})
    monkeypatch.setattr(importer,'fetch_image',lambda url:content.getvalue())
    assert importer.main(['--limit','1']) == 0
    manifest=json.loads((tmp_path/'data/vehicle_images/manifest.json').read_text())
    assert manifest['toyota_test']['creator']=='Author'
    assert manifest['toyota_test']['license']=='CC BY-SA 4.0'
    assert manifest['toyota_test']['sha256']
    assert not (tmp_path/'data/vehicle_images/manifest.tmp').exists()
    with Image.open(tmp_path/manifest['toyota_test']['path']) as photo:assert photo.format=='WEBP'


def test_photo_response_preserves_attribution_headers(monkeypatch,tmp_path):
    from PIL import Image
    import api.vehicle_reference_routes as routes
    Image.new('RGB',(5,5),'blue').save(tmp_path/'image.png')
    monkeypatch.setattr(routes,'project_root',lambda:tmp_path)
    monkeypatch.setattr(routes,'reference_vehicles',lambda:[{'id':'car','image':{
        'path':'image.png','kind':'wikimedia_commons','creator':'Անուն',
        'license':'CC BY 4.0','source_page':'https://commons.wikimedia.org/wiki/File:Car.png'}}])
    response=routes.image('car')
    assert response.headers['x-image-license']=='CC BY 4.0'
    assert response.headers['x-image-credit'].startswith('%')


def test_wikimedia_requests_are_encoded_and_downloads_bounded(monkeypatch):
    import catalog_sources.wikimedia as wiki
    class Response:
        def __init__(self, data, url='https://upload.wikimedia.org/photo.png'):self.data=data; self.url=url
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):return self.data[:limit]
        def geturl(self):return self.url
    requests=[]
    def open_json(request,timeout):
        requests.append(request.full_url)
        assert timeout == 20
        return Response(b'{"query":{"pages":[]}}')
    monkeypatch.setattr(wiki,'urlopen',open_json)
    assert wiki.fetch_json('en.wikipedia.org',action='query',titles='Škoda Octavia')['query']['pages']==[]
    assert '%C5%A0koda' in requests[0]
    monkeypatch.setattr(wiki,'urlopen',lambda *a,**kw:Response(b'photo'))
    assert wiki.fetch_image('https://upload.wikimedia.org/photo.png') == b'photo'
    with pytest.raises(ValueError):wiki.fetch_image('http://localhost/private')
    monkeypatch.setattr(wiki,'urlopen',lambda *a,**kw:Response(b'bad','http://localhost/private'))
    with pytest.raises(ValueError):wiki.fetch_image('https://upload.wikimedia.org/photo.png')
    monkeypatch.setattr(wiki,'MAX_IMAGE_BYTES',2)
    monkeypatch.setattr(wiki,'urlopen',lambda *a,**kw:Response(b'oversized'))
    with pytest.raises(ValueError):wiki.fetch_image('https://upload.wikimedia.org/photo.png')


def test_missing_article_or_commons_image_is_reported_without_fake_photo():
    with pytest.raises(ValueError):image_metadata('Missing',get=lambda *a,**kw:{'query':{'pages':[]}})
    def no_commons(host,**params):
        if host=='en.wikipedia.org':return {'query':{'pages':[{'pageimage':'Car.jpg'}]}}
        return {'query':{'pages':[]}}
    with pytest.raises(ValueError):image_metadata('Car',get=no_commons)


def test_reference_lookup_and_image_url_do_not_depend_on_database():
    import api.main as main
    with TestClient(main.app) as client:
        profile = client.get('/api/v1/vehicle-reference/compatibility',params={'make':'Toyota','model':'Prius','year':2011,'market':'us'}).json()
        assert profile['market']=='US' and profile['observed_protocol'] is None
        assert all(p.startswith('can-') for p in profile['candidates'])
        image = client.get('/api/v1/vehicle-reference/image',params={'make':'Toyota','model':'Corolla','chassis':'E140/E150'})
        assert image.status_code==200 and image.content.startswith(b'\x89PNG')
        assert client.get('/api/v1/vehicle-reference/image',params={'make':'Missing','model':'Missing','chassis':'Missing'}).status_code==404


def test_all_selector_generations_have_unique_transparent_backend_portraits():
    from hashlib import sha256
    from PIL import Image
    from obd.catalog import project_root
    root = project_root()
    cars = reference_vehicles()
    digests = set()
    for car in cars:
        path = root/car['image']['path']
        with Image.open(path) as portrait:
            assert portrait.format == 'PNG' and portrait.mode == 'RGBA', car['id']
            low, high = portrait.getchannel('A').getextrema()
            assert low == 0 and high > 128, car['id']
        digests.add(sha256(path.read_bytes()).hexdigest())
        assert car['image']['url'] == f"/api/v1/vehicle-reference/{car['id']}/image"
    assert len(digests) == len(cars)


def test_new_generations_and_lada_are_available_through_shared_selector():
    assert selector_entries(make='Lada',model='Vesta',year=2017)
    assert selector_entries(make='Toyota',model='Corolla',year=2021,chassis='E210')
    diesel = selector_entries(make='Audi',model='Q5',engine='CGLC 2.0 TDI',year=2012)
    assert diesel and all(row['fuel'] == ['diesel'] and not row['fitment_verified'] for row in diesel)
