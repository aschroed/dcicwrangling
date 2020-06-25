from src.scripts import tagger as t


def test_make_tag_patch_no_existing_tags():
    item = {'uuid': 'a'}
    tag = 'test_tag'
    patch = t.make_tag_patch(item, tag)
    assert patch.get('tags')
    assert patch['tags'][0] == tag


def test_make_tag_patch_w_existing_tags():
    item = {'uuid': 'a', 'tags': ['my_tag']}
    tag = 'test_tag'
    patch = t.make_tag_patch(item, tag)
    assert patch.get('tags')
    tags = patch.get('tags')
    assert len(tags) == 2
    assert tag in tags
    assert 'my_tag' in tags
