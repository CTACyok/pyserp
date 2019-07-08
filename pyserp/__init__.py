import functools
import inspect
import typing


class InjectionError(Exception):
    pass


class Consumer:
    """Wrapper for callable that substitutes it's missing arguments"""

    def __init__(self, cbl, inj: 'Injector'):
        self._callable = cbl
        self._injector = inj
        self._signature = inspect.signature(self._callable)
        self._parameters: typing.Mapping[
            str, inspect.Parameter] = self._signature.parameters
        functools.update_wrapper(self, cbl)

    def __call__(self, **kwargs) -> typing.Any:
        # TODO: support positional arguments
        raise NotImplementedError()


class SyncConsumer(Consumer):
    def __call__(self, **kwargs):
        for name, param in self._parameters.items():
            if name not in kwargs:
                kwargs[name] = self._injector.get_provided(param.annotation)
        return self._callable(**kwargs)


class AsyncConsumer(Consumer):
    async def __call__(self, **kwargs):
        for name, param in self._parameters.items():
            if name not in kwargs:
                kwargs[name] = await self._injector.get_provided(
                    param.annotation)
        return await self._callable(**kwargs)


class Provider:
    """An abstract provider"""

    def __init__(self, cbl):
        self._callable = cbl
        # Calls for `inspect.signature` are cached
        self._signature = inspect.signature(self._callable)
        self._return_annotation = self._signature.return_annotation

    @property
    def provides(self) -> typing.Any:
        return self._return_annotation

    def provide(self):
        raise NotImplementedError()


class SyncProvider(Provider):
    """An abstract provider"""

    def provide(self):
        raise NotImplementedError()


class SingletonProvider(SyncProvider):
    """Provider of the same object for every call"""
    __PLACEHOLDER = object()

    def __init__(self, cbl):
        super().__init__(cbl)
        self._provided = self.__PLACEHOLDER

    def provide(self):
        if self._provided is self.__PLACEHOLDER:
            self._provided = self._callable()
        return self._provided


class FactoryProvider(SyncProvider):
    """Provider of a new object for every call"""

    def provide(self):
        return self._callable()


class AsyncProvider(Provider):
    """An abstract provider"""

    async def provide(self):
        raise NotImplementedError()


class SingletonAsyncProvider(AsyncProvider):
    """Provider of the same object for every call"""
    __PLACEHOLDER = object()

    def __init__(self, cbl):
        super().__init__(cbl)
        self._provided = self.__PLACEHOLDER

    async def provide(self):
        if self._provided is self.__PLACEHOLDER:
            self._provided = await self._callable()
        return self._provided


class FactoryAsyncProvider(AsyncProvider):
    """Provider of a new object for every call"""

    async def provide(self):
        return await self._callable()


class Injector:
    """The Injector. Registers providers and binds them to consumers"""

    def __init__(
            self, name: str = '',
            parent: typing.Optional['Injector'] = None):
        """Do not create instances manually. Use pyserp.get_injector()"""
        self._name = name
        self._parent = parent
        self._children: typing.MutableMapping[str, Injector] = {}
        self._providers: typing.MutableMapping[typing.Any, Provider] = {}

    def consumer(
            self, cbl: typing.Union[typing.Callable[..., typing.Any], Consumer]
    ) -> Consumer:
        """Wrap a callable to have it's arguments auto wired"""
        if isinstance(cbl, Consumer):
            return cbl
        if inspect.iscoroutinefunction(cbl):
            return AsyncConsumer(cbl, self)
        return Consumer(cbl, self)

    def provider(self, cbl: typing.Callable[..., typing.Any]) -> Consumer:
        """Wrap a callable into a Consumer and inject it's return value further
            as a singleton"""
        cons = self.consumer(cbl)
        # noinspection PyUnusedLocal
        prov: Provider
        if inspect.iscoroutinefunction(cbl):
            prov = SingletonAsyncProvider(cons)
        else:
            prov = SingletonProvider(cons)
        self._providers[prov.provides] = prov
        return cons

    def factory(self, cbl: typing.Callable[..., typing.Any]) -> Consumer:
        """Wrap a callable into a Consumer and inject it's return value further
            by calling it every time"""
        cons = self.consumer(cbl)
        # noinspection PyUnusedLocal
        prov: Provider
        if inspect.iscoroutinefunction(cbl):
            prov = FactoryAsyncProvider(cons)
        else:
            prov = FactoryProvider(cons)
        self._providers[prov.provides] = prov
        return cons

    def get_child(self, name: str) -> 'Injector':
        """Get or create a child-scoped injector
        :param name: comma-separated name to build a scope tree on
        """
        inj: Injector = self
        for name_part in name.split('.'):
            child: typing.Optional[Injector] = inj._children.get(name_part)
            if child is None:
                child = inj._children[name_part] = Injector(name_part, inj)
            inj = child
        return inj

    def _get_provider(self, annotation: typing.Any) -> Provider:
        """Get a provider for annotation"""
        prov = self._providers.get(annotation)
        if not prov:
            # Get provider from parent and cache in self
            if not self._parent:
                raise InjectionError(
                    f"Annotation '{annotation}' has no provider")
            prov = self._providers[annotation] = \
                self._parent._get_provider(annotation)
        return prov

    def get_provided(self, annotation: typing.Any) -> typing.Any:
        """Get a provided value for annotation"""
        return self._get_provider(annotation).provide()


def get_injector(name: str = '') -> Injector:
    """Build scoped injector
    :param name: comma-separated name to build a scope tree on
    """
    if name == '':
        return root
    return root.get_child(name)


root = Injector()

consumer = root.consumer
provider = root.provider
factory = root.factory
