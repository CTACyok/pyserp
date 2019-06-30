import pytest

import pyserp


def test_default():
    class A:
        pass

    class B:
        pass

    a = A()
    b = B()

    @pyserp.inject
    def consumer_a_b(a_: A, b_: B):
        assert a_ is a
        assert b_ is b

    @pyserp.provide
    def bean() -> A:
        return a

    consumer_a_b(b_=b)


def test_default_not_provided():
    class A:
        pass

    class B:
        pass

    a = A()

    # noinspection PyUnusedLocal
    @pyserp.inject
    def consumer_a_b(a_: A, b_: B):
        pass

    @pyserp.provide
    def bean() -> A:
        return a

    with pytest.raises(pyserp.InjectionError):
        consumer_a_b()
