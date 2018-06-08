import pytest
from scripts import generate_wfr_from_pf as gw


def test_filter_none_no_nones(capsys):
    l1 = ['a', 'b', 'c']
    l2 = gw._filter_none(l1)
    assert l1 == l2
    out = capsys.readouterr()[0]
    assert not out


def test_filter_none_some_nones(capsys):
    l1 = ['a', None, None, 'd']
    l2 = gw._filter_none(l1)
    assert len(l2) == 2
    out = capsys.readouterr()[0]
    assert out == "WARNING: None values found in your list\n"


# TO BE CONTINUED

def test_remove_skipped_vals_w_good_atids(mocker):
    side_effect = ['uuid1', 'uuid2', 'uuid1', 'uuid2', 'uuid3']
    val = ['id1', 'id2']
    vals2skip = ['id1', 'id2', 'id3']
    # import pdb; pdb.set_trace()
    with mocker.patch('scripts.script_utils.get_item_uuid',
                      side_effect=side_effect):
        result = rj.remove_skipped_vals(val, vals2skip)
        assert not result


def test_remove_skipped_vals_w_item_lookup(mocker):
    side_effect = ['uuid1', 'uuid2', 'uuid1']
    val = ['id1', 'id2']
    vals2skip = ['id1']
    # import pdb; pdb.set_trace()
    with mocker.patch('scripts.script_utils.get_item_uuid',
                      side_effect=side_effect):
        result = rj.remove_skipped_vals(val, vals2skip)
        assert result[0] == val[1]


def test_remove_skipped_vals_w_item_lookup_and_not_found(mocker):
    side_effect = ['uuid1', None, 'uuid3', 'uuid1', None]
    val = ['id1', 'id2', 'id3']
    vals2skip = ['id3', 'id4']
    # import pdb; pdb.set_trace()
    with mocker.patch('scripts.script_utils.get_item_uuid',
                      side_effect=side_effect):
        result = rj.remove_skipped_vals(val, vals2skip)
        assert result[0] == val[0]


@pytest.fixture
def old_pub():
    return {
        'title': 'The Title',
        'authors': ['moe', 'curly'],
        'ID': 'doi:1234',
        'date_published': '2018-01-01',
        'published_by': '4DN',
        'exp_sets_prod_in_pub': ['4DNES1234567', '4DNES7654321'],
        'exp_sets_used_in_pub': ['4DNES1111111'],
        'categories': ['basic biology']
    }


@pytest.fixture
def new_pub():
    return {
        'title': 'The Title',
        'authors': ['moe', 'curly'],
        'ID': 'PMID:1',
        'date_published': '2018-12-31',
    }


@pytest.fixture
def fields2move():
    return [
        'categories',
        'exp_sets_prod_in_pub',
        'exp_sets_used_in_pub',
        'published_by'
    ]


def test_create_patch_for_new_from_old_patch_all(old_pub, new_pub, fields2move):
    patch, s = rj.create_patch_for_new_from_old(old_pub, new_pub, fields2move)
    for f, v in patch.items():
        assert old_pub[f] == patch[f]
    assert not s


def test_create_patch_for_new_from_old_patch_some(old_pub, new_pub, fields2move):
    dfield = 'exp_sets_used_in_pub'
    del old_pub[dfield]
    patch, s = rj.create_patch_for_new_from_old(old_pub, new_pub, fields2move)
    for f, v in patch.items():
        assert old_pub[f] == patch[f]
    assert dfield not in patch
    assert not s


def test_create_patch_for_new_from_old_patch_none(old_pub, new_pub, fields2move):
    for f in fields2move:
        del old_pub[f]
    patch, s = rj.create_patch_for_new_from_old(old_pub, new_pub, fields2move)
    assert not patch
    assert not s


def test_create_patch_for_new_from_old_patch_w_skipped(old_pub, new_pub, fields2move):
    sfield = 'exp_sets_used_in_pub'
    new_pub[sfield] = 'existing val'
    patch, s = rj.create_patch_for_new_from_old(old_pub, new_pub, fields2move)
    assert sfield not in patch
    assert s[sfield]['old'] == ['4DNES1111111']
    assert s[sfield]['new'] == 'existing val'


def test_create_patch_for_new_from_old_patch_w_val2skip(old_pub, new_pub, fields2move):
    v2s = ['4DNES1111111']
    patch, s = rj.create_patch_for_new_from_old(old_pub, new_pub, fields2move, v2s)
    assert 'exp_sets_used_in_pub' not in patch


def test_create_patch_for_new_from_old_patch_w_val2skip_w_multival(old_pub, new_pub, fields2move):
    v2s = ['4DNES7654321']
    patch, s = rj.create_patch_for_new_from_old(old_pub, new_pub, fields2move, v2s)
    assert len(patch['exp_sets_prod_in_pub']) == 1
    assert patch['exp_sets_prod_in_pub'][0] == '4DNES1234567'


def test_move_old_url_to_new_aka_w_existing_aka(old_pub, new_pub):
    old_pub['url'] = 'oldurl'
    new_pub['aka'] = 'my old name'
    p = {'field': 'value'}
    patch, s = rj.move_old_url_to_new_aka(old_pub, new_pub, p, {})
    assert p == patch
    assert s['aka']['new'] == 'oldurl'
    assert s['aka']['old'] == 'my old name'


def test_move_old_url_to_new_aka_w_no_url(old_pub, new_pub):
    new_pub['aka'] = 'my old name'
    p = {'field': 'value'}
    patch, s = rj.move_old_url_to_new_aka(old_pub, new_pub, p, {})
    assert p == patch
    assert not s


def test_move_old_url_to_new_aka_do_transfer(old_pub, new_pub):
    old_pub['url'] = 'oldurl'
    patch, s = rj.move_old_url_to_new_aka(old_pub, new_pub, {}, {})
    assert 'aka' in patch
    assert patch['aka'] == 'oldurl'
    assert not s


@pytest.fixture
def pdict():
    return {
        'exp_sets_prod_in_pub': ['4DNES1111111'],
        'published_by': '4DN'
    }


def test_patch_and_report_w_dryrun_no_data(capsys, auth):
    result = rj.patch_and_report(auth, None, None, None, True)
    out = capsys.readouterr()[0]
    assert 'DRY RUN - nothing will be patched to database' in out
    assert 'NOTHING TO PATCH - ALL DONE!' in out
    assert result is True


def test_patch_and_report_w_skipped_no_patch(capsys, auth):
    skip = {
        'published_by': {'old': 'external', 'new': '4DN'},
        'categories': {'old': ['basic science'], 'new': ['methods']}
    }
    s1 = 'Field: published_by\tHAS: 4DN\tNOT ADDED: external'
    s2 = "Field: categories\tHAS: ['methods']\tNOT ADDED: ['basic science']"
    result = rj.patch_and_report(auth, None, skip, 'test_uuid', False)
    out = capsys.readouterr()[0]
    assert 'WARNING! - SKIPPING for test_uuid' in out
    assert s1 in out
    assert s2 in out
    assert 'NOTHING TO PATCH - ALL DONE!' in out
    assert result is True


def test_patch_and_report_w_patch(capsys, mocker, auth, pdict):
    with mocker.patch('scripts.rxiv2ja.patch_metadata', return_value={'status': 'success'}):
        result = rj.patch_and_report(auth, pdict, None, 'test_uuid', False)
        out = capsys.readouterr()[0]
        assert 'PATCHING - test_uuid' in out
        for k, v in pdict.items():
            s = '%s \t %s' % (k, v)
            assert s in out
        assert 'SUCCESS!' in out
        assert result is True


def test_patch_and_report_w_fail(capsys, mocker, auth, pdict):
    with mocker.patch('scripts.rxiv2ja.patch_metadata', return_value={'status': 'error', 'description': 'woopsie'}):
        result = rj.patch_and_report(auth, pdict, None, 'test_uuid', False)
        out = capsys.readouterr()[0]
        assert 'PATCHING - test_uuid' in out
        for k, v in pdict.items():
            s = '%s \t %s' % (k, v)
            assert s in out
        assert 'FAILED TO PATCH' in out
        assert 'woopsie' in out
        assert not result


def test_find_and_patch_item_references_no_refs(capsys, mocker, auth):
    old_uuid = 'old_uuid'
    new_uuid = 'new_uuid'
    output = "No references to %s found." % old_uuid
    with mocker.patch('scripts.rxiv2ja.scu.get_item_ids_from_args', return_value=[]):
        result = rj.find_and_patch_item_references(auth, old_uuid, new_uuid, False)
        out = capsys.readouterr()[0]
        assert output in out
        assert result is True


def test_find_and_patch_item_references_w_refs(mocker, auth):
    old_uuid = 'old_uuid'
    new_uuid = 'new_uuid'
    with mocker.patch('scripts.rxiv2ja.scu.get_item_ids_from_args', return_value=['bs_uuid', 'ex_uuid']):
        with mocker.patch('scripts.rxiv2ja.patch_and_report', side_effect=[True, True]):
            result = rj.find_and_patch_item_references(auth, old_uuid, new_uuid, False)
            assert result is True


def test_find_and_patch_item_references_w_refs_one_fail(mocker, auth):
    old_uuid = 'old_uuid'
    new_uuid = 'new_uuid'
    with mocker.patch('scripts.rxiv2ja.scu.get_item_ids_from_args', return_value=['bs_uuid', 'ex_uuid1', 'ex_uuid2']):
        with mocker.patch('scripts.rxiv2ja.patch_and_report', side_effect=[True, False, True]):
            result = rj.find_and_patch_item_references(auth, old_uuid, new_uuid, False)
            assert not result
