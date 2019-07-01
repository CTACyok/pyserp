import pytest

import pyserp


@pytest.fixture
def injector() -> pyserp.Injector:
    """New private injector separated from common root"""
    return pyserp.Injector()
