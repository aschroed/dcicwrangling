import pytest
from scripts import patch_field_for_many_items as pf


def test_pffmi_get_args_required_default():
    defaults = {
        'dbupdate': False,
        'env': 'data',
        'key': None,
        'search': False,
        'isarray': False,
        'field': 'status',
        'value': 'deleted',
        'numtype': None
    }
    args = pf.get_args(['i', 'status', 'deleted'])
    for k, v in defaults.items():
        assert getattr(args, k) == v
    assert args.input == ['i']


def test_pffmi_get_args_missing_required(capsys):
    with pytest.raises(SystemExit) as pe:
        pf.get_args(['i', 'status'])
        out = capsys.readouterr()[0]
        assert 'error: the following arguments are required: value' in out
    assert pe.type == SystemExit
    assert pe.value.code == 2


class MockedNamespace(object):
    def __init__(self, dic):
        for k, v in dic.items():
            setattr(self, k, v)


@pytest.fixture
def mocked_args_no_args():
    return MockedNamespace({})


@pytest.fixture
def mocked_args_dbupd_is_false():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': False,
            'search': False,
            'isarray': False,
            'input': ['id1', 'id2'],
            'field': 'status',
            'value': 'deleted',
            'numtype': None
        }
    )


@pytest.fixture
def mocked_args_dbupd_is_true():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': True,
            'search': False,
            'isarray': False,
            'input': ['id1', 'id2'],
            'field': 'status',
            'value': 'deleted',
            'numtype': None
        }
    )


@pytest.fixture
def mocked_args_is_array():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': False,
            'search': False,
            'isarray': True,
            'input': ['id1', 'id2'],
            'field': 'aliases',
            'value': "'4dn-dcic-lab:test'",
            'numtype': None
        }
    )


@pytest.fixture
def mocked_args_w_delete():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': True,
            'search': False,
            'isarray': False,
            'input': ['id1', 'id2'],
            'field': 'aliases',
            'value': '*delete*',
            'numtype': None
        }
    )


def test_pffmi_main_no_auth(mocker, capsys, mocked_args_no_args):
    with pytest.raises(SystemExit):
        with mocker.patch('scripts.patch_field_for_many_items.get_args',
                          return_value=mocked_args_no_args):
            pf.main()
            out = capsys.readouterr()[0]
            assert out == "Authentication failed"


def test_pffmi_main_dryrun(mocker, capsys, mocked_args_dbupd_is_false, auth):
    iids = ['id1', 'id2']
    with mocker.patch('scripts.patch_field_for_many_items.get_args',
                      return_value=mocked_args_dbupd_is_false):
        with mocker.patch('scripts.patch_field_for_many_items.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.patch_field_for_many_items.scu.get_item_ids_from_args',
                              return_value=iids):
                pf.main()
                out = capsys.readouterr()[0]
                for i in iids:
                    s = "PATCHING %s to status = deleted" % i
                    assert s in out


def test_pffmi_main_val_is_array(mocker, capsys, mocked_args_is_array, auth):
    iids = ['id1', 'id2']
    with mocker.patch('scripts.patch_field_for_many_items.get_args',
                      return_value=mocked_args_is_array):
        with mocker.patch('scripts.patch_field_for_many_items.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.patch_field_for_many_items.scu.get_item_ids_from_args',
                              return_value=iids):
                pf.main()
                out = capsys.readouterr()[0]
                for i in iids:
                    s = "PATCHING %s to aliases = ['4dn-dcic-lab:test']" % i
                    assert s in out


def test_pffmi_main_dbupdate(mocker, capsys, mocked_args_dbupd_is_true, auth):
    iids = ['id1', 'id2']
    resp1 = {'status': 'success'}
    resp2 = {'status': 'error', 'description': "access denied"}
    with mocker.patch('scripts.patch_field_for_many_items.get_args',
                      return_value=mocked_args_dbupd_is_true):
        with mocker.patch('scripts.patch_field_for_many_items.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.patch_field_for_many_items.scu.get_item_ids_from_args',
                              return_value=iids):
                with mocker.patch('scripts.patch_field_for_many_items.patch_metadata',
                                  side_effect=[resp1, resp2]):
                    pf.main()
                    out = capsys.readouterr()[0]
                    s1 = "PATCHING %s to status = deleted" % iids[0]
                    s2 = "FAILED TO PATCH %s RESPONSE STATUS error access denied" % iids[1]
                    assert s1 in out
                    assert s2 in out
                    assert 'SUCCESS' in out


def test_pffmi_main_dbupdate_delete(mocker, capsys, mocked_args_w_delete, auth):
    iids = ['id1', 'id2']
    resp1 = {'status': 'success'}
    with mocker.patch('scripts.patch_field_for_many_items.get_args',
                      return_value=mocked_args_w_delete):
        with mocker.patch('scripts.patch_field_for_many_items.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.patch_field_for_many_items.scu.get_item_ids_from_args',
                              return_value=iids):
                with mocker.patch('scripts.patch_field_for_many_items.delete_field',
                                  side_effect=[resp1, resp1]):
                    pf.main()
                    out = capsys.readouterr()[0]
                    for i in iids:
                        s = "PATCHING %s to aliases = *delete*" % i
                        assert s in out
                        assert 'SUCCESS' in out
