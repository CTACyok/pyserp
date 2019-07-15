import pytest

import pyserp


def test_default(injector):
    """Multi-test:
        - dependencies must be providable
        - dependencies must not be provided if parameters passed explicitly
        - argument without provider must be passed explicitly
        - provider must be called only once
        - factory must be called every time it used
    """
    class A:
        pass

    class B:
        pass

    class C:
        pass

    a = A()
    b = B()
    c = C()
    call_counter = {'provider': 0, 'factory': 0}

    @injector.consumer
    def consumer_a_b_c(b_: B, a_: A, c_: C):
        assert a_ is a
        assert b_ is b
        assert c_ is c

    @injector.provider
    def bean() -> A:
        call_counter['provider'] += 1
        return a

    @injector.factory
    def fact() -> C:
        call_counter['factory'] += 1
        return c

    consumer_a_b_c(b)
    consumer_a_b_c(b_=b)
    consumer_a_b_c(b, a, c)
    consumer_a_b_c(b, c_=c)
    assert call_counter['provider'] == 1
    assert call_counter['factory'] == 2


def test_default_not_provided(injector):
    """Injector must throw an error for unresolved dependency"""
    class A:
        pass

    class B:
        pass

    a = A()

    # noinspection PyUnusedLocal
    @injector.consumer
    def consumer_a_b(a_: A, b_: B):
        pass

    @injector.provider
    def bean() -> A:
        return a

    with pytest.raises(pyserp.InjectionError):
        consumer_a_b()


def test_root():
    """Root injector must be accessible by package calls"""
    root = pyserp.get_injector()
    root2 = pyserp.get_injector('')
    assert root is pyserp.root
    assert root2 is root
    assert pyserp.consumer.__self__ is root
    assert pyserp.provider.__self__ is root
    assert pyserp.factory.__self__ is root


def test_method_consumer(injector):
    """Methods must be mark-able as consumers"""
    class A:
        pass

    a = A()

    class B:
        @injector.consumer
        def __init__(self, a_: A):
            self.a = a_

        @injector.consumer
        def get_a(self, a_: A):
            return a_

        @classmethod
        @injector.consumer  # FIXME: make consumer mark-able above `@classmethod`
        def static_get_a(cls, a_: A):
            assert cls is B
            return a_

    @injector.provider
    def bean() -> A:
        return a

    assert B().a is a

    assert B().get_a() is a
    assert B.static_get_a() is a
