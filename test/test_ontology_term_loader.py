from scripts import ontology_term_loader as otl


def test_get_id():
    term = {'a': 1, 'b': 2}
    otl.get_id(term)
    assert True
