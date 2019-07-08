import pytest

import pyserp


@pytest.mark.asyncio
async def test_default(injector):
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
    async def consumer_a_b_c(a_: A, b_: B, c_: C):
        assert a_ is a
        assert b_ is b
        assert c_ is c

    @injector.provider
    async def bean() -> A:
        call_counter['provider'] += 1
        return a

    @injector.factory
    async def fact() -> C:
        call_counter['factory'] += 1
        return c

    await consumer_a_b_c(b_=b)
    await consumer_a_b_c(b_=b)
    await consumer_a_b_c(a_=a, b_=b, c_=c)
    assert call_counter['provider'] == 1
    assert call_counter['factory'] == 2


@pytest.mark.asyncio
async def test_default_not_provided(injector):
    """Injector must throw an error for unresolved dependency"""
    class A:
        pass

    class B:
        pass

    a = A()

    # noinspection PyUnusedLocal
    @injector.consumer
    async def consumer_a_b(a_: A, b_: B):
        pass

    @injector.provider
    async def bean() -> A:
        return a

    with pytest.raises(pyserp.InjectionError):
        await consumer_a_b()
