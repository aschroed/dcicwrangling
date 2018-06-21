from scripts import geo2fdn as geo
from Bio import Entrez
import pytest

@pytest.fixture
def email():
    return '4dndcic@gmail.com'

def test_parse_gsm_with_sra():
    pass

def test_parse_gsm_dbgap():
    pass

def test_parse_bs_xml():
    pass

def test_get_geo_metadata_seq(email):
    Entrez.email = email
    gse = geo.get_geo_metadata('GSE93431', filepath='./test/data_files/GSE93431_family.soft.gz')
    assert len([exp for exp in gse.experiments if exp.exptype == 'hic']) == 6
    assert len([exp for exp in gse.experiments if exp.exptype == 'chipseq']) == 14
    assert len([exp for exp in gse.experiments if exp.exptype == 'rnaseq']) == 12
    assert len([bs for bs in gse.biosamples]) == 32


def test_get_geo_metadata_microarray(email, capfd):
    Entrez.email = email
    gse = geo.get_geo_metadata('GSE102960', filepath='./test/data_files/GSE102960_family.soft.gz')
    out, err = capfd.readouterr()
    assert not gse
    assert out == 'Sequencing experiments not found. Exiting.\n'


# modify_xls test

# modify_xls test with experiment_type

# experiment_type_compare tests?
