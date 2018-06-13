import pytest
from copy import deepcopy as cp
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


@pytest.fixture
def prov_workflow():
    return {
        "award": "1U01CA200059-01",
        "lab": "4dn-dcic-lab",
        "app_name": "file-provenance-tracker",
        "uuid": "bef50397-4d72-4ed1-9c78-100e14e5c47f",
        "name": "file-provenance-tracker",
        "title": "File Provenance Tracking Workflow",
        "description": "Takes one or more input files and traces to a single output Processed File",
        "aliases": ["4dn-dcic-lab:file-provenance-wf"],
        "workflow_type": "Other",
        "category": "provenance",
        "arguments": [
            {
                "argument_type": "Input file",
                "workflow_argument_name": "inputs"
            },
            {
                "argument_type": "Output processed file",
                "workflow_argument_name": "outputs"
            }
        ],
        "steps": [
            {
                "inputs": [
                    {
                        "meta": {
                            "cardinality": "array",
                            "global": True,
                            "type": "data file"
                        },
                        "name": "inputs",
                        "source": [
                            {
                                "name": "inputs"
                            }
                        ]
                    }
                ],
                "meta": {
                    "analysis_step_types": [
                        "tracking"
                    ],
                    "description": "Provenance Tracking"
                },
                "name": "Provenance Tracking",
                "outputs": [
                    {
                        "meta": {
                            "cardinality": "single",
                            "global": True,
                            "type": "data file"
                        },
                        "name": "outputs",
                        "target": [
                            {
                                "name": "outputs"
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def fp_data():
    return {
        "lab": "4dn-dcic-lab",
        "award": "1U01CA200059-01",
        "file_type": "LADs",
        "description": "5 kb Associated domains (LADs) - replicate 2",
        "file_size": 106884,
        "@type": ["FileProcessed", "File", "Item"],
        "status": "uploaded",
        "uuid": "658ecf64-57a1-41aa-ac04-7224c7ed3207",
        "accession": "4DNFIYQBRZMZ",
        "file_format": "bed",
        "filename": "file.bed.gz"
    }


@pytest.fixture
def infiles(fp_data):
    b1 = cp(fp_data)
    b2 = cp(fp_data)
    b1['file_format'] = b2['file_format'] = 'bam'
    b1['file_type'] = b2['file_type'] = 'alignment'
    b1['filename'] = 'bamfile1.bam'
    b2['filename'] = 'bamfile2.bam'
    b1['description'] = 'replicate 2 LMNB1 alignment file'
    b2['description'] = 'replicate 2 DAM-only alignment file'
    b1['uuid'] = "658ecf64-57a1-41aa-ac04-7224c7ed3208"
    b2['uuid'] = "658ecf64-57a1-41aa-ac04-7224c7ed3209"
    b1["accession"] = "4DNFIYQBRZMA"
    b2["accession"] = "4DNFIYQBRZMB"
    return [b1, b2]


@pytest.fixture
def outfile(fp_data):
    return [fp_data]


@pytest.fixture
def wfr_out_json():
    return {
        'workflow': 'bef50397-4d72-4ed1-9c78-100e14e5c47f',
        'aliases': ['4dn-dcic-lab:file-provenance-tracker_run_2018-06-11-16-29-22.839062'],
        'award': '1U01CA200059-01',
        'lab': '4dn-dcic-lab',
        'status': 'in review by lab',
        'title': 'File Provenance Tracking Workflow run on 2018-06-11 16:29:22.839062',
        'run_status': 'complete',
        'input_files': [
            {'workflow_argument_name': 'inputs', 'value': '658ecf64-57a1-41aa-ac04-7224c7ed3208', 'ordinal': 1},
            {'workflow_argument_name': 'inputs', 'value': '658ecf64-57a1-41aa-ac04-7224c7ed3209', 'ordinal': 2}
        ],
        'output_files': [
            {'workflow_argument_name': 'outputs', 'value': '658ecf64-57a1-41aa-ac04-7224c7ed3207',
             'workflow_argument_format': 'bed', 'type': 'Output processed file'}
        ]
    }


def test_get_attribution_with_attr(infiles):
    award, lab = gw.get_attribution(infiles)
    assert award == infiles[0]['award']
    assert lab == infiles[0]['lab']


def test_get_attribution_with_attr_in_second(infiles):
    infiles[1]['award'] = 'test_award'
    infiles[1]['lab'] = 'test_lab'
    del infiles[0]['award']
    del infiles[0]['lab']
    award, lab = gw.get_attribution(infiles)
    assert award == infiles[1]['award']
    assert lab == infiles[1]['lab']


def test_get_attribution_attr_topsy_turvy_gets_dcic(infiles):
    del infiles[0]['award']
    del infiles[1]['lab']
    award, lab = gw.get_attribution(infiles)
    assert award == 'b0b9c607-f8b4-4f02-93f4-9895b461334b'
    assert lab == '828cd4fe-ebb0-4b36-a94a-d2e3a36cc989'


def test_get_attribution_attr_none_gets_dcic(infiles):
    del infiles[0]['award']
    del infiles[0]['lab']
    del infiles[1]['award']
    del infiles[1]['lab']
    award, lab = gw.get_attribution(infiles)
    assert award == 'b0b9c607-f8b4-4f02-93f4-9895b461334b'
    assert lab == '828cd4fe-ebb0-4b36-a94a-d2e3a36cc989'


def test_get_attribution_attr_embedded_objs(infiles):
    infiles[0]['award'] = {'uuid': 'test_award_uuid'}
    infiles[0]['lab'] = {'uuid': 'test_lab_uuid'}
    award, lab = gw.get_attribution(infiles)
    assert award == 'test_award_uuid'
    assert lab == 'test_lab_uuid'


def test_create_wfr_meta_only_json(auth, prov_workflow, infiles, outfile, wfr_out_json):
    eqfields = ['workflow', 'award', 'lab', 'status', 'run_status']
    chkstart = ['aliases', 'title']
    wfr_json = gw.create_wfr_meta_only_json(auth, prov_workflow, infiles, outfile)
    for f, v in wfr_json.items():
        if f in eqfields:
            assert v == wfr_out_json[f]
        elif f in chkstart:
            if f == 'aliases':
                v = v[0]
                wfr_out_json[f] = wfr_out_json[f][0]
            assert v.startswith(wfr_out_json[f][:35])
        elif f.startswith('input'):
            assert len(v) == 2
            for d in v:
                assert d['workflow_argument_name'] == 'inputs'
                assert 'ordinal' in d
                assert d['value'] in ['658ecf64-57a1-41aa-ac04-7224c7ed3208', '658ecf64-57a1-41aa-ac04-7224c7ed3209']
        else:
            assert len(v) == 1
            for d in v:
                assert d['workflow_argument_name'] == 'outputs'
                assert d['value'] == '658ecf64-57a1-41aa-ac04-7224c7ed3207'
                assert d['workflow_argument_format'] == 'bed'
                assert d['type'] == 'Output processed file'


def test_create_wfr_meta_only_json_w_no_wf_uuid(mocker, auth, prov_workflow):
    del prov_workflow['uuid']
    with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_if_you_can', return_value=prov_workflow):
        wfr_json = gw.create_wfr_meta_only_json(auth, prov_workflow, None, None)
        assert wfr_json is None


def test_create_wfr_meta_only_json_w_alias_and_desc(mocker, auth, prov_workflow, infiles, outfile):
    alias = 'test_alias'
    desc = 'test description'
    with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_if_you_can',
                      side_effect=[prov_workflow, infiles[0], infiles[1], outfile[0]]):
        with mocker.patch('scripts.generate_wfr_from_pf.datetime', return_value='2018-06-11 16:29:22.839062'):
            wfr_json = gw.create_wfr_meta_only_json(auth, prov_workflow, infiles, outfile, alias=alias, description=desc)
            assert wfr_json['description'] == desc
            assert wfr_json['aliases'][0] == alias


def test_create_wfr_meta_only_json_no_in_or_out_files(mocker, auth, prov_workflow):
    with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_if_you_can',
                      return_value=prov_workflow):
        with mocker.patch('scripts.generate_wfr_from_pf.datetime', return_value='2018-06-11 16:29:22.839062'):
            wfr_json = gw.create_wfr_meta_only_json(auth, prov_workflow, [], [])
            assert 'input_files' not in wfr_json
            assert 'output_files' not in wfr_json


def test_create_wfr_meta_only_json_no_workflow_args(mocker, auth, prov_workflow, infiles, outfile):
    del prov_workflow['arguments']
    with mocker.patch('scripts.generate_wfr_from_pf.scu.get_item_if_you_can',
                      side_effect=[prov_workflow, infiles[0], infiles[1], outfile[0]]):
        with mocker.patch('scripts.generate_wfr_from_pf.datetime', return_value='2018-06-11 16:29:22.839062'):
            wfr_json = gw.create_wfr_meta_only_json(auth, prov_workflow, infiles, outfile)
            assert 'input_files' not in wfr_json
            assert 'output_files' not in wfr_json
