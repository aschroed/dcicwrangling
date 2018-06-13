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


# @pytest.fixture
# def key():
#     return {'key': 'k', 'secret': 'ss', 'server': 'https://data.4dnucleome.org'}
#
#
# def test_get_args_w_options(key):
#     options = {
#         'dbupdate': True,
#         'env': 'staging',
#         'include_released': True,
#         'key': key,
#         'no_children': ['Vendor', 'Individual'],
#         'search': True,
#         'types2exclude': ['Protocol'],
#         'types2include': ['Organism', 'Ontology']
#     }
#     # import pdb; pdb.set_trace()
#     args = gli.get_args("i --dbuupdate --env staging --include_released \
#         --key {'key': 'k', 'secret': 'ss', 'server': 'https://data.4dnucleome.org'} \
#         --no_children Vendor Individual --search --types2exclude Protocol --types2include Organism Ontology")
#     for k, v in options.items():
#         assert getattr(args, k) == v
#     assert args.input == ['i']
