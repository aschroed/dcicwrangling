from scripts import geo2fdn as geo
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
        with mocker.patch('Bio.Entrez.efetch', return_value=samn):
            return geo.parse_bs_record('SAMN06219555')


@pytest.fixture
def exp_with_sra(mocker, srx_file):
    with open(srx_file, 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value=srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2715320.txt')
            return geo.parse_gsm(gsm)


@pytest.fixture
def exp_with_sra_pe(mocker):
    with open('./test/data_files/SRX1839065.xml', 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value=srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2198225.txt')
            return geo.parse_gsm(gsm)


@pytest.fixture
def hidden_sra(mocker):
    with open('./test/data_files/SRX4191023.xml', 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value=srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2715320.txt')
            return geo.parse_gsm(gsm)


def test_parse_gsm_with_sra(mocker, srx_file):
    with open(srx_file, 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value=srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2715320.txt')
            exp = geo.parse_gsm(gsm)
    assert exp.link in srx_file
    assert exp.exptype == 'repliseq'
    assert exp.bs == 'SAMN06219555'
    assert exp.layout == 'single'
    assert exp.instr == 'Ion Torrent Proton'
    assert len(exp.runs) == 1
    assert exp.length == 51


def test_parse_gsm_dbgap(mocker):
    with open('./test/data_files/SRX3028942.xml', 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value=srx):
            gsm = GEOparse.get_GEO(filepath='./test/data_files/GSM2254215.txt')
            exp = geo.parse_gsm(gsm)
    assert exp.bs == 'SAMN05449633'
    assert not exp.layout
    assert exp.instr == 'Illumina HiSeq 2500'
    assert exp.exptype.startswith('hic')
    assert not exp.link
    assert not exp.runs
    assert not exp.length


def test_experiment_bad_sra(mocker, capfd):
    with open('./test/data_files/SRX0000000.xml', 'r') as srx:
        with mocker.patch('Bio.Entrez.efetch', return_value=srx):
            exp = geo.Experiment('hic', 'Illumina HiSeq 2500', 'GSM1234567',
                                 'title', 'SAMN05449633', 'SRX0000000')
            exp.get_sra()
    out, err = capfd.readouterr()
    assert "Couldn't parse" in out


def gsm_soft_to_exp_obj(mocker, gsm_file, exp_type=None):
    with mocker.patch('scripts.geo2fdn.Experiment.get_sra'):
        gsm = GEOparse.get_GEO(filepath=gsm_file)
        return geo.parse_gsm(gsm, experiment_type=exp_type)


def test_parse_gsm_exptypes(mocker):
    soft_file_dict = {'GSM3154187': 'dna sprite', 'GSM2198225': 'capturec',
                      'GSM3149191': 'atacseq', 'GSM2586973': 'damidseq', 'GSM3003988': 'chiapet'}
    for acc in soft_file_dict.keys():
        parsed = gsm_soft_to_exp_obj(mocker, './test/data_files/' + acc + '.txt')
        assert parsed.exptype == soft_file_dict[acc]


def test_parse_bs_record(mocker):
    with open('./test/data_files/SAMN06219555.xml', 'r') as samn:
        with mocker.patch('Bio.Entrez.efetch', return_value=samn):
            bs = geo.parse_bs_record('SAMN06219555')
    for item in ['tamoxifen', 'liver', 'NIPBL', 'Nipbl(flox/flox)']:
        assert item in bs.description


def test_get_geo_metadata_seq(mocker):
    with mocker.patch('scripts.geo2fdn.Experiment.get_sra'):
        with mocker.patch('scripts.geo2fdn.parse_bs_record', return_value='SAMNXXXXXXXX'):
            gse = geo.get_geo_metadata('./test/data_files/GSE93431_family.soft.gz')
    assert len([exp for exp in gse.experiments if exp.exptype == 'hic']) == 6
    assert len([exp for exp in gse.experiments if exp.exptype == 'chipseq']) == 14
    assert len([exp for exp in gse.experiments if exp.exptype == 'rnaseq']) == 12
    assert len([bs for bs in gse.biosamples]) == 32


def test_get_geo_metadata_microarray(capfd):
    gse = geo.get_geo_metadata('./test/data_files/GSE102960_family.soft.gz')
    out, err = capfd.readouterr()
    assert not gse
    assert out == 'Sequencing experiments not found. Exiting.\n'


def test_get_geo_metadata_bad_accession(capfd):
    gse = geo.get_geo_metadata('GDS102960')
    out, err = capfd.readouterr()
    assert not gse
    assert out == 'Input not a valid GEO accession.\n'


def test_get_geo_metadata_sra_hidden(capfd, mocker, hidden_sra):
    gse_all = GEOparse.get_GEO(filepath='./test/data_files/GSE93431_family.soft.gz')
    with mocker.patch('scripts.geo2fdn.parse_bs_record', return_value='SAMNXXXXXXXX'):
        with mocker.patch('scripts.geo2fdn.parse_gsm', return_value=hidden_sra):
            gse = geo.get_geo_metadata('./test/data_files/GSE93431_family.soft.gz')
    out, err = capfd.readouterr()
    assert not gse
    assert len(gse_all.gsms.values()) > 10


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


def test_get_geo_tables(mocker, bs_obj, exp_with_sra):
    mocker.patch('scripts.geo2fdn.parse_gsm', return_value=exp_with_sra)
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    geo.get_geo_tables('GSM2715320', './test/data_files/test_table', email='test@email.com')
    with open('./test/data_files/test_table_fqs.tsv', 'r') as fq_file:
        fq_out = fq_file.readlines()
    assert not any('paired with' in line for line in fq_out)
    for item in ['expts', 'fqs', 'bs']:
        os.remove('./test/data_files/test_table_{}.tsv'.format(item))


def test_get_geo_tables_pe(mocker, bs_obj, exp_with_sra_pe):
    mocker.patch('scripts.geo2fdn.parse_gsm', return_value=exp_with_sra_pe)
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    geo.get_geo_tables('GSM2198225', './test/data_files/test_table', email='test@email.com')
    with open('./test/data_files/test_table_fqs.tsv', 'r') as fq_file:
        fq_out = fq_file.readlines()
    assert all('paired with' in line for line in fq_out)
    for item in ['expts', 'fqs', 'bs']:
        os.remove('./test/data_files/test_table_{}.tsv'.format(item))


def test_modify_xls(mocker, bs_obj, exp_with_sra):
    mocker.patch('scripts.geo2fdn.parse_gsm', return_value=exp_with_sra)
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    # gds = geo.get_geo_metadata('GSM2715320', filepath='./test/data_files/GSM2715320.txt')
    geo.modify_xls('./test/data_files/GSM2715320.txt', './test/data_files/repliseq_template.xls', 'out.xls', 'abc')
    book = xlrd.open_workbook('out.xls')
    outfile_dict = create_xls_dict(book)
    os.remove('out.xls')
    assert outfile_dict['Biosample']['aliases'][0].startswith('abc:')
    assert outfile_dict['Biosample']['dbxrefs'][0].startswith('BioSample:SAMN')
    # assert BiosampleCellCulture has alias
    assert (outfile_dict['BiosampleCellCulture']['aliases'][0].startswith('abc:')
            and outfile_dict['BiosampleCellCulture']['aliases'][0].endswith('-cellculture'))
    # assert BiosampleCellCulture alias is in Biosample sheet
    assert (outfile_dict['Biosample']['cell_culture_details'][0].startswith('abc:')
            and outfile_dict['Biosample']['cell_culture_details'][0].endswith('-cellculture'))
    # FileFastq assert(s)
    assert outfile_dict['FileFastq']['*file_format'][0] == 'fastq'
    assert not outfile_dict['FileFastq']['paired_end'][0]
    assert not (outfile_dict['FileFastq']['related_files.relationship_type'][0]
                or outfile_dict['FileFastq']['related_files.file'][0])
    assert outfile_dict['FileFastq']['read_length'][0]
    assert outfile_dict['FileFastq']['instrument'][0]
    assert outfile_dict['FileFastq']['dbxrefs'][0].startswith('SRA:SRR')
    # ExperimentRepliseq assert(s)
    assert outfile_dict['ExperimentRepliseq']['dbxrefs'][0].startswith('GEO:GSM')
    assert outfile_dict['ExperimentRepliseq']['description'][0]
    assert outfile_dict['ExperimentRepliseq']['files'][0]
    assert outfile_dict['ExperimentRepliseq']['*biosample'][0]


def test_modify_xls_pe(mocker, bs_obj, exp_with_sra_pe):
    mocker.patch('scripts.geo2fdn.parse_gsm', return_value=exp_with_sra_pe)
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    geo.modify_xls('./test/data_files/GSM2198225.txt',
                   './test/data_files/capturec_seq_template.xls',
                   'out_pe.xls', 'abc')
    book = xlrd.open_workbook('out_pe.xls')
    outfile_dict = create_xls_dict(book)
    os.remove('out_pe.xls')
    # FileFastq assert(s)
    assert outfile_dict['FileFastq']['*file_format'][0] == 'fastq'
    assert outfile_dict['FileFastq']['paired_end'][0]
    assert (outfile_dict['FileFastq']['related_files.relationship_type'][0]
            and outfile_dict['FileFastq']['related_files.file'][0])
    assert outfile_dict['FileFastq']['read_length'][0]
    assert outfile_dict['FileFastq']['instrument'][0]
    assert outfile_dict['FileFastq']['dbxrefs'][0].startswith('SRA:SRR')


def test_modify_xls_some_unparsable_types(mocker, capfd, bs_obj):
    mocker.patch('scripts.geo2fdn.Experiment.get_sra')
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    geo.modify_xls('./test/data_files/GSE87585_family.soft.gz',
                   './test/data_files/capturec_seq_template.xls', 'out2.xls', 'abc')
    out, err = capfd.readouterr()
    book = xlrd.open_workbook('out2.xls')
    outfile_dict = create_xls_dict(book)
    os.remove('out2.xls')
    assert len(outfile_dict['ExperimentSeq']['aliases']) > 0
    types_in_outfile = outfile_dict['ExperimentSeq']['*experiment_type']
    lines = out.split('\n')
    assert 'RNA-seq' in types_in_outfile and len(types_in_outfile) == 6
    assert 'ExperimentCaptureC' not in outfile_dict.keys()
    assert 'The following accessions had experiment types that could not be parsed:' in lines
    assert 'HiC experiments found in ./test/data_files/GSE87585_family.soft.gz but no ExperimentHiC sheet' in lines


def test_modify_xls_set_experiment_type(mocker, capfd, bs_obj):
    mocker.patch('scripts.geo2fdn.Experiment.get_sra')
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    geo.modify_xls('./test/data_files/GSE87585_family.soft.gz',
                   './test/data_files/capturec_seq_template.xls', 'out3.xls', 'abc',
                   experiment_type='CaptureC')
    book = xlrd.open_workbook('out3.xls')
    out, err = capfd.readouterr()
    outfile_dict = create_xls_dict(book)
    os.remove('out3.xls')
    assert 'ExperimentSeq' not in outfile_dict.keys()
    assert len(outfile_dict['ExperimentCaptureC']['aliases']) == 12
    assert 'The following accessions had experiment types that could not be parsed:' not in out.split('\n')


def test_modify_xls_no_sheets(mocker, bs_obj):
    mocker.patch('scripts.geo2fdn.Experiment.get_sra')
    mocker.patch('scripts.geo2fdn.parse_bs_record', return_value=bs_obj)
    geo.modify_xls('./test/data_files/GSE87585_family.soft.gz',
                   './test/data_files/no_template.xls', 'out4.xls', 'abc',
                   experiment_type='CaptureC')
    book = xlrd.open_workbook('out4.xls')
    outfile_dict = create_xls_dict(book)
    os.remove('out4.xls')
    assert not outfile_dict


def run_compare(capfd, exp_with_sra, template, exp_type, sheet):
    inbook = xlrd.open_workbook(template)
    exp_list = [exp for exp in [exp_with_sra] if exp.exptype == exp_type]
    acc = exp_with_sra.geo
    geo.experiment_type_compare(sheet, exp_list, acc, inbook)
    out, err = capfd.readouterr()
    return out.split('\n'), acc


def test_experiment_type_compare_nosheet_exp(capfd, exp_with_sra):
    out, acc = run_compare(capfd, exp_with_sra, './test/data_files/capturec_seq_template.xls',
                           'repliseq', 'ExperimentRepliseq')
    assert 'Repliseq experiments found in {} but no ExperimentRepliseq sheet'.format(acc) in out


def test_experiment_type_compare_sheet_noexp(capfd, exp_with_sra):
    out, acc = run_compare(capfd, exp_with_sra, './test/data_files/capturec_seq_template.xls',
                           'capturec', 'ExperimentCaptureC')
    assert 'No CaptureC experiments parsed from {}.'.format(acc) in out


def test_experiment_type_compare_sheet_exp(capfd, exp_with_sra):
    out, acc = run_compare(capfd, exp_with_sra, './test/data_files/repliseq_template.xls',
                           'repliseq', 'ExperimentRepliseq')
    assert 'No Repliseq experiments parsed from {}.'.format(acc) not in out
    assert 'Repliseq experiments found in {} but no ExperimentRepliseq sheet'.format(acc) not in out
