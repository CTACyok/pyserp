import pytest

import pyserp


def test_inject_inherited(injector):
    """Dependencies must be providable via child class"""
    class A:
        pass

    class B(A):
        pass

    b = B()

    @injector.consumer
    def consume(a_: A):
        assert a_ is b

    @injector.provider
    def bean() -> B:
        return b

    consume()


def test_inject_prent(injector):
    """Dependencies must not be providable via parent class"""
    class A:
        pass

    class B(A):
        pass

    b = B()

    @injector.consumer
    def consume(a_: B):
        assert a_ is b

    @injector.provider
    def bean() -> A:
        return b

    with pytest.raises(pyserp.InjectionError):
        consume()
