import pytest
from scripts import script_utils as scu
import argparse
from collections import OrderedDict


@pytest.fixture
def eset_json():
    return {
        "schema_version": "2",
        "accession": "4DNES4GSP9S4",
        "award": "4871e338-b07d-4665-a00a-357648e5bad6",
        "alternate_accessions": [],
        "aliases": [
            "ren:HG00512_repset"
        ],
        "experimentset_type": "replicate",
        "status": "released",
        "experiments_in_set": [
            "d4b0e597-8c81-43e3-aeda-e9842fc18e8f",
            "8d10f11f-95a8-4b8d-8ff2-748ea8631a23"
        ],
        "lab": "795847de-20b6-4f8c-ba8d-185215469cbf",
        "public_release": "2017-06-30",
        "uuid": "9eb40c13-cf85-487c-9819-71ef74a22dcc",
        "documents": [],
        "description": "Dilution Hi-C experiment on HG00512",
        "submitted_by": "da4f53e5-4e54-4ae7-ad75-ba47316a8bfa",
        "date_created": "2017-04-28T17:46:08.642218+00:00",
        "replicate_exps": [
            {
                "replicate_exp": "d4b0e597-8c81-43e3-aeda-e9842fc18e8f",
                "bio_rep_no": 1,
                "tec_rep_no": 1
            },
            {
                "replicate_exp": "8d10f11f-95a8-4b8d-8ff2-748ea8631a23",
                "bio_rep_no": 2,
                "tec_rep_no": 1
            }
        ],
    }


@pytest.fixture
def bs_embed_json():
    return {
        "lab": {
            "display_title": "David Gilbert, FSU",
            "uuid": "6423b207-8176-4f06-a127-951b98d6a53a",
            "link_id": "~labs~david-gilbert-lab~",
            "@id": "/labs/david-gilbert-lab/"
        },
        "display_title": "4DNBSLACJHX1"
    }


@pytest.fixture
def profiles():
    return {
        "ExperimentSetReplicate": {
            "title": "Replicate Experiments",
            "description": "Experiment Set for technical/biological replicates.",
            "properties": {
                "tags": {"uniqueItems": "true", "description": "Key words that can tag an item - useful for filtering.", "type": "array", "ff_clear": "clone", "items": {"title": "Tag", "description": "A tag for the item.", "type": "string"}, "title": "Tags"},  # noqa: E501
                "documents": {"uniqueItems": "true", "description": "Documents that provide additional information (not data file).", "type": "array", "default": [], "comment": "See Documents sheet or collection for existing items.", "title": "Documents", "items": {"title": "Document", "description": "A document that provides additional information (not data file).", "type": "string", "linkTo": "Document"}},  # noqa: E501
                "notes": {"exclude_from": ["submit4dn", "FFedit-create"], "title": "Notes", "description": "DCIC internal notes.", "type": "string", "elasticsearch_mapping_index_type": {"title": "Field mapping index type", "description": "Defines one of three types of indexing available", "type": "string", "default": "analyzed", "enum": ["analyzed", "not_analyzed", "no"]}}  # noqa: E501
            }
        },
        "TreatmentChemical": {
            "title": "Chemical Treatment",
            "description": "A Chemical or Drug Treatment on Biosample.",
            "properties": {
                "documents": {"uniqueItems": "true", "description": "Documents that provide additional information (not data file).", "type": "array", "default": [], "comment": "See Documents sheet or collection for existing items.", "title": "Documents", "items": {"title": "Document", "description": "A document that provides additional information (not data file).", "type": "string", "linkTo": "Document"}},  # noqa: E501
                "public_release": {"anyOf": [{"format": "date-time"}, {"format": "date"}], "exclude_from": ["submit4dn", "FFedit-create"], "description": "The date which the item was released to the public", "permission": "import_items", "type": "string", "comment": "Do not submit, value is assigned when released.", "title": "Public Release Date"},  # noqa: E501
            }
        }
    }


def test_is_uuid():
    uuids = [
        '231111bc-8535-4448-903e-854af460b254',
        '231111bc-8535-4448-903e-854af460b25',
        '231111bc85354448903e854af460b254'
    ]
    for i, u in enumerate(uuids):
        if i == 0:
            assert scu.is_uuid(u)
        else:
            assert not scu.is_uuid(u)


def test_find_uuids_from_eset(eset_json):
    field2uuid = {
        "award": "4871e338-b07d-4665-a00a-357648e5bad6",
        "lab": "795847de-20b6-4f8c-ba8d-185215469cbf",
        "uuid": "9eb40c13-cf85-487c-9819-71ef74a22dcc",
        "submitted_by": "da4f53e5-4e54-4ae7-ad75-ba47316a8bfa"
    }
    exps = ["d4b0e597-8c81-43e3-aeda-e9842fc18e8f", "8d10f11f-95a8-4b8d-8ff2-748ea8631a23"]
    for field, val in eset_json.items():
        ulist = scu.find_uuids(val)
        if field in field2uuid:
            assert field2uuid[field] == ulist[0]
        elif field in ["experiments_in_set", "replicate_exps"]:
            for u in ulist:
                assert u in exps


def test_filter_dict_by_value(eset_json):
    to_filter = {
        "schema_version": "2",
        "accession": "4DNES4GSP9S4",
        "aliases": ["ren:HG00512_repset"]
    }
    vals = list(to_filter.values())
    included = scu.filter_dict_by_value(eset_json, vals)
    assert len(included) == len(to_filter)
    for f in to_filter.keys():
        assert f in included

    excluded = scu.filter_dict_by_value(eset_json, vals, include=False)
    assert len(excluded) == len(eset_json) - len(to_filter)
    for f in to_filter.keys():
        assert f not in excluded


def test_has_field_value_check_for_field_only(eset_json):
    fieldnames = ['schema_version', 'award', 'alternate_accessions']
    for f in fieldnames:
        assert scu.has_field_value(eset_json, f)


def test_has_field_value_no_it_doesnt(eset_json):
    fieldnames = ['biosample', 'blah', 'bio_rep_no']
    for f in fieldnames:
        assert not scu.has_field_value(eset_json, f)


def test_has_field_value_check_for_field_and_value(eset_json):
    fields_w_values = {
        "schema_version": "2",
        "accession": "4DNES4GSP9S4",
        "aliases": "ren:HG00512_repset"
    }
    for f, v in fields_w_values.items():
        assert scu.has_field_value(eset_json, f, v)


def test_has_field_value_check_for_field_w_item(bs_embed_json):
    f = "lab"
    v = "/labs/david-gilbert-lab/"
    assert scu.has_field_value(bs_embed_json, f, v, True)


def test_has_field_value_check_for_field_w_item_not_found(bs_embed_json):
    f = "lab"
    v = "/labs/nobodys-lab/"
    assert not scu.has_field_value(bs_embed_json, f, v, True)


def test_has_field_value_check_for_field_w_item_no_dict():
    f = "b"
    v = "/labs/david-gilbert-lab/"
    assert not scu.has_field_value('blah', f, v, True)


def test_has_field_value_value_not_found_in_list(eset_json):
    not_found = 'unfound'
    assert not scu.has_field_value(eset_json, 'experiments_in_set', not_found)


def test_has_field_value_value_not_found_as_string(eset_json):
    not_found = 'unfound'
    assert not scu.has_field_value(eset_json, 'status', not_found)


def test_get_types_that_can_have_field(mocker, profiles):
    field = 'tags'
    with mocker.patch('scripts.script_utils.get_metadata', return_value=profiles):
        types_w_field = scu.get_types_that_can_have_field('conn', field)
        assert 'ExperimentSetReplicate' in types_w_field
        assert 'TreatmentChemical' not in types_w_field


def test_get_item_type_from_dict(eset_json):
    eset_json['@type'] = ['ExperimentSetReplicate', 'ExperimentSet', 'Item']
    es_ty = scu.get_item_type('blah', eset_json)
    assert es_ty == 'ExperimentSetReplicate'


def test_get_item_type_from_id(mocker, auth):
    with mocker.patch('scripts.script_utils.get_metadata', return_value={'@type': ['ExperimentSetReplicate']}):
        result = scu.get_item_type(auth, 'blah')
        assert result == 'ExperimentSetReplicate'


def test_get_item_type_no_type(mocker, auth, capsys):
    with mocker.patch('scripts.script_utils.get_metadata', return_value={'description': 'blah'}):
        result = scu.get_item_type(auth, 'blah')
        out = capsys.readouterr()[0]
        assert out == "Can't find a type for item blah\n"
        assert result is None


@pytest.fixture
def items_w_uuids():
    return [
        {'name': 'one', 'uuid': 'a'},
        {'name': 'two', 'uuid': 'b'},
        {'name': 'three', 'uuid': 'c'},
    ]


def test_get_item_ids_from_list(auth):
    ids = ['a', 'b', 'c']
    result = scu.get_item_ids_from_args(ids, auth)
    for a in [i in ids for i in result]:
        assert a


def test_get_item_ids_from_search(mocker, auth, items_w_uuids):
    ids = ['a', 'b', 'c']
    with mocker.patch('scripts.script_utils.search_metadata', return_value=[]):
        with mocker.patch('scripts.script_utils.get_metadata', return_value=items_w_uuids):
            result = scu.get_item_ids_from_args('search', auth, True)
            for a in [i in ids for i in result]:
                assert a


def test_get_item_uuid_w_uuid(auth):
    uid = '7868f960-50ac-11e4-916c-0800200c9a66'
    result = scu.get_item_uuid(uid, auth)
    assert result == uid


def test_get_item_uuid_w_atid(mocker, auth):
    atid = '/labs/test-lab'
    with mocker.patch('scripts.script_utils.get_metadata',
                      return_value={'uuid': 'test_uuid'}) as mt:
        result = scu.get_item_uuid(atid, auth)
        assert mt.called_with(atid, auth)
        assert result == 'test_uuid'


def test_get_item_uuid_not_found(mocker, auth):
    atid = '/labs/non-lab'
    with mocker.patch('scripts.script_utils.get_metadata',
                      return_value={'status': 'error'}) as mt:
        result = scu.get_item_uuid(atid, auth)
        assert mt.called_with(atid, auth)
        assert result is None


def test_create_ff_arg_parser(capsys):
    helpout = ['--env', '--key', '--dbupdate']
    parser = scu.create_ff_arg_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    parser.print_help()
    out = capsys.readouterr()[0]
    for o in helpout:
        assert o in out


def test_create_input_arg_parser(capsys):
    helpout = ['input', '--search']
    parser = scu.create_input_arg_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    parser.print_help()
    out = capsys.readouterr()[0]
    for o in helpout:
        assert o in out


def test_convert_key_arg_to_dict_good_key():
    inkey = "{'key': 'ABCDEF', 'secret': 'supersecret', 'server': 'https://data.4dnucleome.org'}"
    outkey = scu.convert_key_arg_to_dict(inkey)
    assert outkey == {'key': 'ABCDEF', 'secret': 'supersecret', 'server': 'https://data.4dnucleome.org'}


def test_convert_key_arg_to_dict_bad_key(capsys):
    inkey = "{'key': 'ABCDEF', 'secret': 'supersecret'}"
    with pytest.raises(SystemExit):
        scu.convert_key_arg_to_dict(inkey)
        out = capsys.readouterr()[0]
        assert out == "You included a key argument but it appears to be malformed or missing required info - see --help"


def test_get_linked_items_w_item_in_found(auth):
    itemid = 'itemid'
    found_items = {itemid: 1}
    iid = scu.get_linked_items(auth, itemid, found_items)
    assert itemid in iid


def test_get_linked_items_w_error_status(auth, mocker):
    with mocker.patch('scripts.script_utils.get_metadata', return_value={'status': 'error'}):
        iids = scu.get_linked_items(auth, 'test_id')
        assert not iids


def test_get_linked_items_w_no_type(auth, mocker):
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[{'status': 'released'},
                                   {'field': 'value'}]):
        iids = scu.get_linked_items(auth, 'test_id')
        assert not iids


def test_get_linked_items_w_type_in_no_children(auth, mocker):
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[{'status': 'current'},
                                   {'@type': ['Publication']}]):
        iids = scu.get_linked_items(auth, 'test_id')
        assert iids['test_id'] == 'Publication'


def test_get_linked_items_w_linked_items(auth, mocker):
    goodids = ['test_id', '7256801c-9c6e-4563-a97a-a295fccf5f07']
    badids = ['6256801c-9c6e-4563-a97a-a295fccf5f07']
    resp1 = {
        'status': 'released',
        '@type': ['Biosample', 'Item'],
        'biosource': '7256801c-9c6e-4563-a97a-a295fccf5f07',
        'attachment': '6256801c-9c6e-4563-a97a-a295fccf5f07'
    }
    found = {'7256801c-9c6e-4563-a97a-a295fccf5f07': 'Biosource'}
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[resp1,
                                   {'@type': ['Biosample']}]):
        with mocker.patch('scripts.script_utils.find_uuids',
                          return_value=['7256801c-9c6e-4563-a97a-a295fccf5f07']):
            iids = scu.get_linked_items(auth, 'test_id', found)
            for i in iids:
                assert i in goodids
                assert i not in badids


def test_get_linked_items_w_no_linked_foundids(auth, mocker):
    goodids = ['test_id']
    badids = ['6256801c-9c6e-4563-a97a-a295fccf5f07']
    resp1 = {
        'status': 'released',
        '@type': ['Biosample', 'Item'],
        'biosource': '7256801c-9c6e-4563-a97a-a295fccf5f07',
        'attachment': '6256801c-9c6e-4563-a97a-a295fccf5f07'
    }
    found = {}
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[resp1,
                                   {'@type': ['Biosample']}]):
        with mocker.patch('scripts.script_utils.find_uuids',
                          return_value=None):
            iids = scu.get_linked_items(auth, 'test_id', found)
            for i in iids:
                assert i in goodids
                assert i not in badids


def test_get_linked_item_ids_w_recursive(auth, mocker):
    goodids = ['test_id', '7256801c-9c6e-4563-a97a-a295fccf5f07', '5256801c-9c6e-4563-a97a-a295fccf5f07']
    badids = ['6256801c-9c6e-4563-a97a-a295fccf5f07']
    resp1 = {
        'status': 'released',
        '@type': ['Biosample', 'Item'],
        'biosource': '7256801c-9c6e-4563-a97a-a295fccf5f07',
        'attachment': '6256801c-9c6e-4563-a97a-a295fccf5f07'
    }
    resp1 = OrderedDict(sorted(resp1.items(), key=lambda t: t[0]))
    resp2 = {
        'status': 'released',
        '@type': ['Biosource', 'Item'],
        'biosource_vendor': '5256801c-9c6e-4563-a97a-a295fccf5f07'
    }
    resp2 = OrderedDict(sorted(resp2.items(), key=lambda t: t[0]))
    resp3 = {
        'status': 'released',
    }
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[resp1,
                                   {'@type': ['Biosample']},
                                   resp2,
                                   {'@type': ['Biosource']},
                                   resp3,
                                   {'@type': ['Vendor']}]):
        with mocker.patch('scripts.script_utils.find_uuids',
                          side_effect=[None,
                                       ['7256801c-9c6e-4563-a97a-a295fccf5f07'],
                                       None,
                                       None,
                                       ['5256801c-9c6e-4563-a97a-a295fccf5f07'],
                                       None,
                                       None]):
            iids = scu.get_linked_items(auth, 'test_id')
            for i in iids:
                assert i in goodids
                assert i not in badids


@pytest.fixture
def cell_line_json():
    return {
        "is_slim_for": "cell",
        "namespace": "http://www.ebi.ac.uk/efo",
        "term_id": "EFO:0000322",
        "term_name": "cell line",
        "source_ontology": "530006bc-8535-4448-903e-854af460b254",
        "term_url": "http://www.ebi.ac.uk/efo/EFO_0000322"
    }


def test_get_item_if_you_can_json_w_uuid(auth, eset_json):
    result = scu.get_item_if_you_can(auth, eset_json)
    assert result == eset_json


def test_get_item_if_you_can_w_uuid(mocker, auth, eset_json):
    with mocker.patch('scripts.script_utils.get_metadata', return_value=eset_json):
        result = scu.get_item_if_you_can(auth, eset_json['uuid'])
        assert result == eset_json


def test_get_item_if_you_can_w_termname_and_itype(mocker, auth, cell_line_json):
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[None, cell_line_json]):
        result = scu.get_item_if_you_can(auth, cell_line_json['term_name'], 'OntologyTerm')
        assert result == cell_line_json


def test_get_item_if_you_can_w_termname_and_no_itype_no_item(mocker, auth, cell_line_json):
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[None, None]):
        result = scu.get_item_if_you_can(auth, cell_line_json['term_name'])
        assert result is None


def test_get_item_if_you_can_w_fakename_and_itype_no_item(mocker, auth):
    with mocker.patch('scripts.script_utils.get_metadata',
                      side_effect=[None, None]):
        result = scu.get_item_if_you_can(auth, 'fake name', 'OntologyTerm')
        assert result is None
