from scripts import ontology_term_loader as otl


def test_get_id_no_id():
    term = {'a': 1, 'b': 2}
    idtag = otl.get_id(term)
    assert idtag is None


def test_get_id_w_uuid():
    term = {'uuid': 1, 'b': 2}
    idtag = otl.get_id(term)
    assert idtag == 1


def test_get_id_w_termid():
    term = {'term_id': '4DN:0000001', 'b': 2}
    idtag = otl.get_id(term)
    assert idtag == '4DN:0000001'


def test_get_id_w_term_name():
    term = {'term_name': 'joey', 'b': 2}
    idtag = otl.get_id(term)
    assert idtag == 'joey'


def test_get_id_w_all():
    term = {'uuid': 1, 'term_id': '4DN:0000001', 'term_name': 'joey'}
    idtag = otl.get_id(term)
    assert idtag == 1
