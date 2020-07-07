# import pytest
from scripts import tag_release_freeze as trf
from collections import Counter


def test_has_released_released():
    relstatus = ['released', 'released to project']
    for s in relstatus:
        res = trf.has_released(s)
        assert res is True


def test_has_released_not_released():
    relstatus = ['in review by lab', 'archived', 'deleted', 'current',
                 'submission in progress', 'obsolete']
    for s in relstatus:
        res = trf.has_released(s)
        assert not res


def test_get_attype_w_attype():
    res = {'@type': ['FileFastq', 'File', 'Item']}
    ty = trf.get_attype(res)
    assert ty == 'FileFastq'


def test_get_attype_w_no_attype():
    res = {'uuif': 'test_uuid'}
    ty = trf.get_attype(res)
    assert ty is None


def test_make_tag_patch_already_has_tag(mocker):
    tag = 'test_tag'
    item = {'uuid': 'test_uuid', 'tags': [tag]}
    mocker.patch('scripts.tag_release_freeze.scu.has_field_value', return_value=True)
    result = trf.make_tag_patch(item, tag)
    assert result is None


def test_make_tag_patch_no_existing_tags(mocker):
    tag = 'test_tag'
    item = {'uuid': 'test_uuid'}
    mocker.patch('scripts.tag_release_freeze.scu.has_field_value', return_value=False)
    result = trf.make_tag_patch(item, tag)
    assert len(result['tags']) == 1
    assert tag in result['tags']


def test_make_tag_patch_w_existing_tags(mocker):
    tag = 'test_tag'
    item = {'uuid': 'test_uuid', 'tags': ['old_tag']}
    mocker.patch('scripts.tag_release_freeze.scu.has_field_value', return_value=False)
    result = trf.make_tag_patch(item, tag)
    assert len(result['tags']) == 2
    assert tag in result['tags']
    assert 'old_tag' in result['tags']


def test_do_patch_dry_run(capsys, auth):
    input = ['test_uuid', 'Item', {'tags': ['test_tag']}]
    output = 'DRY RUN - will update %s of type %s with %s\n' % tuple(input)
    cnts = Counter()
    trf.do_patch(*input, auth, False, cnts)
    out = capsys.readouterr()[0]
    assert out == output
    assert cnts['not_patched'] == 1


def test_do_patch_success(capsys, mocker, auth):
    input = ['test_uuid', 'Item', {'tags': ['test_tag']}]
    output = 'UPDATING - %s of type %s with %s\nsuccess\n' % tuple(input)
    cnts = Counter()
    mocker.patch('scripts.tag_release_freeze.patch_metadata', return_value={'status': 'success'})
    trf.do_patch(*input, auth, True, cnts)
    out = capsys.readouterr()[0]
    assert out == output
    assert cnts['patched'] == 1


def test_do_patch_failure(capsys, mocker, auth):
    input = ['test_uuid', 'Item', {'tags': ['test_tag']}]
    err = {'status': 'error'}
    output = 'UPDATING - %s of type %s with %s\n%s\n%s\n' % tuple(input + [err['status'], str(err)])
    cnts = Counter()
    mocker.patch('scripts.tag_release_freeze.patch_metadata', return_value=err)
    trf.do_patch(*input, auth, True, cnts)
    out = capsys.readouterr()[0]
    assert out == output
    assert cnts['errors'] == 1


def test_add_tag2item_no_uid(capsys, mocker, auth):
    mocker.patch('scripts.tag_release_freeze.get_metadata', return_value={'status': 'released'})
    trf.add_tag2item(auth, 'iid', 'test_tag', [], Counter())
    out = capsys.readouterr()[0]
    assert "SEEN OR IDLESS ITEM - SKIPPING" in out


def test_add_tag2item_in_seen(capsys, mocker, auth):
    mocker.patch('scripts.tag_release_freeze.get_metadata', return_value={'status': 'released', 'uuid': 'test_uuid'})
    trf.add_tag2item(auth, 'iid', 'test_tag', ['test_uuid'], Counter())
    out = capsys.readouterr()[0]
    assert "SEEN OR IDLESS ITEM - SKIPPING" in out


def test_add_tag2item_add_the_tag(mocker, auth):
    seen = []
    cnts = Counter()
    mocker.patch('scripts.tag_release_freeze.get_metadata', return_value={'status': 'released', 'uuid': 'test_uuid'})
    mocker.patch('scripts.tag_release_freeze.has_released', return_value=True)
    mocker.patch('scripts.tag_release_freeze.get_attype', return_value=None)
    mocker.patch('scripts.tag_release_freeze.make_tag_patch', return_value={'tags': ['test_tag']})
    mocker.patch('scripts.tag_release_freeze.do_patch')
    trf.add_tag2item(auth, 'iid', 'test_tag', seen, cnts, 'Biosample', True)
    assert 'test_uuid' in seen


def test_add_tag2item_no_patch(capsys, mocker, auth):
    seen = []
    cnts = Counter()
    mocker.patch('scripts.tag_release_freeze.get_metadata', return_value={'status': 'released', 'uuid': 'test_uuid'})
    mocker.patch('scripts.tag_release_freeze.has_released', return_value=True)
    mocker.patch('scripts.tag_release_freeze.get_attype', return_value=None)
    mocker.patch('scripts.tag_release_freeze.make_tag_patch', return_value=None)
    trf.add_tag2item(auth, 'iid', 'test_tag', seen, cnts, 'Biosample', True)
    out = capsys.readouterr()[0]
    assert out == 'NOTHING TO PATCH - skipping test_uuid\n'
    assert cnts['skipped'] == 1
    assert 'test_uuid' in seen


def test_add_tag2item_not_released(capsys, mocker, auth):
    seen = []
    cnts = Counter()
    mocker.patch('scripts.tag_release_freeze.get_metadata', return_value={'status': 'deleted', 'uuid': 'test_uuid'})
    mocker.patch('scripts.tag_release_freeze.has_released', return_value=False)
    trf.add_tag2item(auth, 'iid', 'test_tag', seen, cnts, 'Biosample', True)
    out = capsys.readouterr()[0]
    assert out == "STATUS deleted doesn't get tagged - skipping test_uuid\n"
    assert cnts['skipped'] == 1
    assert 'test_uuid' in seen
