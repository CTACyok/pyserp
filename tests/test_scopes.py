import pytest

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
    assert e._parent._parent._parent is pyserp.root


def test_ascending_search(injector):
    """Dependencies must be discoverable closer to root injector"""
    class A:
        pass

    a = A()

    child = injector.get_child('child')

    @child.consumer
    def service(a_: A):
        assert a_ is a

    @injector.provider
    def bean() -> A:
        return a

    service()


def test_descending_search(injector):
    """Dependencies must not be discoverable farther from root injector"""
    class A:
        pass

    a = A()

    child = injector.get_child('child')

    @injector.consumer
    def service(a_: A):
        assert a_ is a

    @child.provider
    def bean() -> A:
        return a

    with pytest.raises(pyserp.InjectionError):
        service()
