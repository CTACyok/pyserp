import pyserp


def test_build_scoped_injector():
    """Scoped injector must build it's tree properly"""
    e = pyserp.get_injector('q.w.e')
    d = pyserp.get_injector('q.w.d')
    assert e._name == 'e'
    assert d._name == 'd'
    assert e._parent._name == 'w'
    assert e._parent is d._parent
    assert e._parent._parent._name == 'q'
    assert e._parent._parent._parent._name == ''
    assert e._parent._parent._parent is pyserp._root
