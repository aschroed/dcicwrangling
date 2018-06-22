from scripts import geo2fdn as geo
# from Bio import Entrez
import GEOparse
import xlrd
import pytest
import os


@pytest.fixture
def srx_file():
    return './test/data_files/SRX3028942.xml'


@pytest.fixture
def bs_obj(mocker):
    with open('./test/data_files/SAMN06219555.xml', 'r') as samn:
        with mocker.patch('Bio.Entrez.efetch', return_value = samn):
            return geo.parse_bs_record('SAMN06219555')


@pytest.fixture
def exp_with_sra(mocker, srx_file):
    with open(srx_file, 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value = srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2715320.txt')
            return geo.parse_gsm(gsm)


def test_parse_gsm_with_sra(mocker, srx_file):
    with open(srx_file, 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value = srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2715320.txt')
            exp = geo.parse_gsm(gsm)
    assert exp.link in srx_file
    assert exp.exptype == 'repliseq'
    assert exp.bs == 'SAMN07405769'
    assert exp.layout == 'single'
    assert exp.instr == 'Ion Torrent Proton'
    assert len(exp.runs) == 1
    assert exp.length == 51


def test_parse_gsm_dbgap(mocker):
    with open('./test/data_files/SRX3028942.xml', 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value = srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2254215.txt')
            exp = geo.parse_gsm(gsm)
    assert exp.bs == 'SAMN05449633'
    assert not exp.layout
    assert exp.instr == 'Illumina HiSeq 2500'
    assert exp.exptype.startswith('hic')
    assert not exp.link
    assert not exp.runs
    assert not exp.length

# test gsm parse with different experiment types autodetected
    # mock get_sra
    # ['dnase hic', 'rnaseq', 'tsaseq', 'chipseq', 'capturec',
    #    'atacseq', 'damid', 'damidseq', 'chiapet']
    # multiple functions or all one function?

def gsm_soft_to_exp_obj(mocker, gsm_file, exp_type=None):
    with mocker.patch('scripts.geo2fdn.Experiment.get_sra'):
        gsm = GEOparse.get_GEO(filepath=gsm_file)
        return geo.parse_gsm(gsm, experiment_type=exp_type)


def test_parse_gsm_sprite(mocker):
    sprite = gsm_soft_to_exp_obj(mocker, './test/data_files/GSM3154187.txt')
    assert sprite.exptype == 'dna sprite'

def test_parse_gsm_capturec():
    pass


def test_parse_gsm_atacseq():
    pass


def test_parse_gsm_damid():
    pass


def test_parse_gsm_chiapet():
    pass


def test_parse_bs_record(mocker):
    with open('./test/data_files/SAMN06219555.xml', 'r') as samn:
        with mocker.patch('Bio.Entrez.efetch', return_value = samn):
            bs = geo.parse_bs_record('SAMN06219555')
    for item in ['tamoxifen', 'liver', 'NIPBL', 'Nipbl(flox/flox)']:
        assert item in bs.description


def test_get_geo_metadata_seq(mocker):
    with mocker.patch('scripts.geo2fdn.Experiment.get_sra'):
        with mocker.patch('scripts.geo2fdn.parse_bs_record', return_value = 'SAMNXXXXXXXX'):
            gse = geo.get_geo_metadata('GSE93431', filepath='./test/data_files/GSE93431_family.soft.gz')
    assert len([exp for exp in gse.experiments if exp.exptype == 'hic']) == 6
    assert len([exp for exp in gse.experiments if exp.exptype == 'chipseq']) == 14
    assert len([exp for exp in gse.experiments if exp.exptype == 'rnaseq']) == 12
    assert len([bs for bs in gse.biosamples]) == 32


def test_get_geo_metadata_microarray(capfd):
    gse = geo.get_geo_metadata('GSE102960', filepath='./test/data_files/GSE102960_family.soft.gz')
    out, err = capfd.readouterr()
    assert not gse
    assert out == 'Sequencing experiments not found. Exiting.\n'


def create_xls_dict(inbook):
    xls_dict = {}
    for name in inbook.sheet_names():
        current_sheet = inbook.sheet_by_name(name)
        if current_sheet.nrows > 4:
            headers = [current_sheet.cell_value(0, i) for i in range(1, current_sheet.ncols)]
            col_dict = {}
            for header in headers:
                col_dict[header] = [current_sheet.cell_value(j, headers.index(header) + 1) for
                                    j in range(4, current_sheet.nrows)]
            xls_dict[name] = col_dict
    return xls_dict


def test_modify_xls(mocker, bs_obj, exp_with_sra):
    with mocker.patch('scripts.geo2fdn.parse_gsm', return_value = exp_with_sra):
        with mocker.patch('scripts.geo2fdn.parse_bs_record', return_value = bs_obj):
            # gds = geo.get_geo_metadata('GSM2715320', filepath='./test/data_files/GSM2715320.txt')
            geo.modify_xls('GSM2715320', './test/data_files/repliseq_template.xls', 'out.xls', 'abc')
    book = xlrd.open_workbook('out.xls')
    outfile_dict = create_xls_dict(book)
    os.remove('out.xls')
    assert outfile_dict['Biosample']['aliases'][0].startswith('abc:')
    assert outfile_dict['Biosample']['dbxrefs'][0].startswith('BioSample:SAMN')
    # assert BiosampleCellCulture has alias
    assert (outfile_dict['BiosampleCellCulture']['aliases'][0].startswith('abc:') and
            outfile_dict['BiosampleCellCulture']['aliases'][0].endswith('-cellculture'))
    # assert BiosampleCellCulture alias is in Biosample sheet
    assert (outfile_dict['Biosample']['cell_culture_details'][0].startswith('abc:') and
            outfile_dict['Biosample']['cell_culture_details'][0].endswith('-cellculture'))
    # FileFastq assert(s)
    assert outfile_dict['FileFastq']['*file_format'][0] == 'fastq'
    assert not outfile_dict['FileFastq']['paired_end'][0]
    assert not (outfile_dict['FileFastq']['related_files.relationship_type'][0] or
                outfile_dict['FileFastq']['related_files.file'][0])
    assert outfile_dict['FileFastq']['read_length'][0]
    assert outfile_dict['FileFastq']['instrument'][0]
    assert outfile_dict['FileFastq']['dbxrefs'][0].startswith('SRA:SRR')
    # ExperimentRepliseq assert(s)
    assert outfile_dict['ExperimentRepliseq']['dbxrefs'][0].startswith('GEO:GSM')
    assert outfile_dict['ExperimentRepliseq']['description'][0]
    assert outfile_dict['ExperimentRepliseq']['files'][0]
    assert outfile_dict['ExperimentRepliseq']['*biosample'][0]

    # compare saved excel to data_file excel
    # delete saved excel
    # modify original function to return outbook rather than save to file?

# modify_xls test with experiment_type
#     exp = gsm_soft_to_exp_obj('./test/data_files/GSM2648491.txt')
# above: unparsable captureC experiment


# experiment_type_compare tests?

def test_experiment_type_compare_sheet_noexp():
    pass


def test_experiment_type_compare_nosheet_exp():
    pass
