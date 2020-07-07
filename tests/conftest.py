import pytest


@pytest.fixture
def auth():
    return {
        "server": "https://data.4dnucleome.org/",
        "key": "testkey",
        "secret": "testsecret"
    }
