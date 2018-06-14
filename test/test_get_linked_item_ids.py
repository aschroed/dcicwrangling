import pytest
from scripts import get_linked_item_ids as gli


def test_get_excluded_w_nothing():
    exclude = ['User', 'Lab', 'Award', 'OntologyTerm', 'Ontology', 'Organism', 'Publication']
    types = gli.get_excluded()
    assert sorted(exclude) == sorted(types)


def test_get_excluded_w_excludes():
    to_exclude = ['Biosample', 'Vendor', 'Award']
    types = gli.get_excluded(to_exclude)
    for te in to_exclude:
        assert te in types


def test_get_excluded_w_includes():
    to_include = ['User', 'Award']
    types = gli.get_excluded(include_types=to_include)
    for ti in to_include:
        assert ti not in types


def test_get_excluded_w_both():
    to_exclude = ['Biosample', 'Vendor', 'Award']
    to_include = ['User', 'Award']  # with Award in both it should be included
    types = gli.get_excluded(to_exclude, to_include)
    for te in to_exclude:
        if te == 'Award':
            continue
        assert te in types
    for ti in to_include:
        assert ti not in types


def test_is_released_released(mocker, auth):
    with mocker.patch('scripts.get_linked_item_ids.get_metadata',
                      return_value={'status': 'released'}):
        ans = gli.is_released('iid', auth)
        assert ans is True


def test_is_released_not_released(mocker, auth):
    with mocker.patch('scripts.get_linked_item_ids.get_metadata',
                      return_value={'status': 'deleted'}):
        ans = gli.is_released('iid', auth)
        assert not ans


def test_is_released_no_status(mocker, auth):
    with mocker.patch('scripts.get_linked_item_ids.get_metadata',
                      return_value={'description': 'blah'}):
        ans = gli.is_released('iid', auth)
        assert not ans


def test_gl_get_args_required_default():
    defaults = {
        'dbupdate': False,
        'env': 'data',
        'include_released': False,
        'key': None,
        'no_children': None,
        'search': False,
        'types2exclude': None,
        'types2include': None
    }
    args = gli.get_args('i')
    for k, v in defaults.items():
        assert getattr(args, k) == v
    assert args.input == ['i']


class MockedNamespace(object):
    def __init__(self, dic):
        for k, v in dic.items():
            setattr(self, k, v)


@pytest.fixture
def mocked_args_no_args():
    return MockedNamespace({})


@pytest.fixture
def mocked_args_standard():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': False,
            'input': 'i',
            'search': False,
            'types2exclude': None,
            'types2include': None,
            'no_children': None,
            'include_released': False,
        }
    )


@pytest.fixture
def mocked_args_plus():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': False,
            'input': 'i',
            'search': False,
            'types2exclude': None,
            'types2include': None,
            'no_children': ['Biosample'],
            'include_released': True,
        }
    )


@pytest.fixture
def mocked_args_plus_more():
    return MockedNamespace(
        {
            'key': None,
            'env': 'prod',
            'dbupdate': False,
            'input': 'i',
            'search': False,
            'types2exclude': None,
            'types2include': None,
            'no_children': ['Biosample'],
            'include_released': False,
        }
    )


@pytest.fixture
def got_item_ids():
    return {
        'test_eset_uuid': 'ExperimentSetReplicate',
        'ret_uuid1': 'ExperimentHiC',
        'ret_uuid2': 'ExperimentHiC',
        'ret_uuid3': 'Biosample',
        'ret_uuid4': 'Biosample',
        'ret_uuid5': 'Protocol'
    }


def test_gl_main_no_auth(mocker, capsys, mocked_args_no_args):
    with pytest.raises(SystemExit):
        with mocker.patch('scripts.get_linked_item_ids.get_args',
                          return_value=mocked_args_no_args):
            gli.main()
            out = capsys.readouterr()[0]
            assert out == "Authentication failed"


def test_gl_main_standard(mocker, capsys, mocked_args_standard, auth, got_item_ids):
    se = [False] * 6
    with mocker.patch('scripts.get_linked_item_ids.get_args',
                      return_value=mocked_args_standard):
        with mocker.patch('scripts.get_linked_item_ids.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_ids_from_args',
                              return_value=['test_eset_uuid']):
                with mocker.patch('scripts.get_linked_item_ids.get_excluded',
                                  return_value=['User', 'Lab', 'Award', 'OntologyTerm', 'Ontology',
                                                'Organism', 'Publication', 'IndividualHuman']):
                    with mocker.patch('scripts.get_linked_item_ids.scu.get_linked_items',
                                      return_value=got_item_ids):
                        with mocker.patch('scripts.get_linked_item_ids.scu.filter_dict_by_value',
                                          return_value=got_item_ids):
                            with mocker.patch('scripts.get_linked_item_ids.is_released',
                                              side_effect=se):
                                gli.main()
                                out = capsys.readouterr()[0]
                                for f, v in got_item_ids.items():
                                    assert f in out
                                    assert v in out


def test_gl_main_plus(mocker, capsys, mocked_args_plus, auth, got_item_ids):
    se = [False] * 5 + [True]
    with mocker.patch('scripts.get_linked_item_ids.get_args',
                      return_value=mocked_args_plus):
        with mocker.patch('scripts.get_linked_item_ids.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_ids_from_args',
                              return_value=['test_eset_uuid']):
                with mocker.patch('scripts.get_linked_item_ids.get_excluded',
                                  return_value=None):
                    with mocker.patch('scripts.get_linked_item_ids.scu.get_linked_items',
                                      return_value=got_item_ids):
                            with mocker.patch('scripts.get_linked_item_ids.is_released',
                                              side_effect=se):
                                gli.main()
                                out = capsys.readouterr()[0]
                                for f, v in got_item_ids.items():
                                    assert f in out
                                    assert v in out


def test_gl_main_plus_more(mocker, capsys, mocked_args_plus_more, auth, got_item_ids):
    se = [False] * 5 + [True] + [False]
    with mocker.patch('scripts.get_linked_item_ids.get_args',
                      return_value=mocked_args_plus_more):
        with mocker.patch('scripts.get_linked_item_ids.get_authentication_with_server',
                          return_value=auth):
            with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_ids_from_args',
                              return_value=['test_eset_uuid', 'test_eset_uuid2']):
                with mocker.patch('scripts.get_linked_item_ids.get_excluded',
                                  return_value=None):
                    with mocker.patch('scripts.get_linked_item_ids.scu.get_linked_items',
                                      side_effect=[got_item_ids, {'ret_uuid1': got_item_ids['ret_uuid1']}]):
                            with mocker.patch('scripts.get_linked_item_ids.is_released',
                                              side_effect=se):
                                gli.main()
                                out = capsys.readouterr()[0]
                                for f, v in got_item_ids.items():
                                    assert f in out
                                    assert v in out
