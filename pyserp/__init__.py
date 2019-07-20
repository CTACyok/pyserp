"""
Experimental provider-consumer injection mechanism for python
"""
import functools
import inspect
import typing


class InjectionError(Exception):
    """General 'something-went-wrong' error"""
    pass


# Note to self: You can not wrap a method in class with method __call__,
#   because argument 'self' of method is erased with instance of wrapper
def _consumer_factory(cbl, inj: 'Injector'):
    """Wrap callable to substitute it's missing arguments"""
    if getattr(cbl, '__is_consumer__', False):
        return cbl
    signature = inspect.signature(cbl)
    parameters: typing.Mapping[str, inspect.Parameter] = signature.parameters
    if inspect.iscoroutinefunction(cbl):
        @functools.wraps(cbl)
        async def _decorator(*args, **kwargs):
            arguments = signature.bind_partial(*args, **kwargs).arguments
            for name, param in parameters.items():
                if name not in arguments and param.annotation is not inspect.Parameter.empty:
                    arguments[name] = await inj.get_provider(param.annotation).provide_async()
            return await cbl(**arguments)
    else:
        @functools.wraps(cbl)
        def _decorator(*args, **kwargs):
            arguments = signature.bind_partial(*args, **kwargs).arguments
            for name, param in parameters.items():
                if name not in arguments and param.annotation is not inspect.Parameter.empty:
                    arguments[name] = inj.get_provider(param.annotation).provide()
            return cbl(**arguments)
    setattr(_decorator, '__is_consumer__', True)
    return _decorator


class Provider:
    """Common provider interface"""
    @property
    def provides(self) -> typing.Any:
        """Property for provider to tell what it holds"""
        raise NotImplementedError()

    def provide(self):
        """Provide a value in a synchronous matter"""
        raise NotImplementedError()

    async def provide_async(self):
        """Provide a value in an asynchronous matter"""
        raise NotImplementedError()


class CallableProvider(Provider):
    """An abstract callable-based provider"""

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

    async def provide_async(self):
        raise NotImplementedError()


class SyncProvider(CallableProvider):
    """An abstract provider"""

    def provide(self):
        raise NotImplementedError()

    async def provide_async(self):
        return self.provide()


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


class AsyncProvider(CallableProvider):
    """An abstract provider"""

    def provide(self):
        raise InjectionError('Asynchronous provider can not be used synchronously')

    async def provide_async(self):
        raise NotImplementedError()


class SingletonAsyncProvider(AsyncProvider):
    """Provider of the same object for every call"""
    __PLACEHOLDER = object()

    def __init__(self, cbl):
        super().__init__(cbl)
        self._provided = self.__PLACEHOLDER

    async def provide_async(self):
        if self._provided is self.__PLACEHOLDER:
            self._provided = await self._callable()
        return self._provided


class FactoryAsyncProvider(AsyncProvider):
    """Provider of a new object for every call"""

    async def provide_async(self):
        return await self._callable()


class Service(Provider):
    """A synchronous singleton class-based provider"""
    __PLACEHOLDER = object()

    def __init__(self, cls: typing.Type[typing.Any]):
        self._cls = cls
        self._provided = self.__PLACEHOLDER

    @property
    def provides(self) -> typing.Any:
        return self._cls

    def provide(self):
        if self._provided is self.__PLACEHOLDER:
            self._provided = self._cls()
        return self._provided

    async def provide_async(self):
        return self.provide()


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

    def consumer(self, cbl: typing.Callable[..., typing.Any]):
        """Wrap a callable to have it's arguments auto wired"""
        return _consumer_factory(cbl, self)

    def provider(self, cbl: typing.Callable[..., typing.Any]):
        """Wrap a callable into a Consumer and inject it's return value further
            as a singleton"""
        cons = self.consumer(cbl)
        # noinspection PyUnusedLocal
        prov: CallableProvider
        if inspect.iscoroutinefunction(cbl):
            prov = SingletonAsyncProvider(cons)
        else:
            prov = SingletonProvider(cons)
        if inspect.isclass(prov.provides):
            for _cls in inspect.getmro(prov.provides):
                self._providers[_cls] = prov
        else:
            self._providers[prov.provides] = prov
        return cons

    def factory(self, cbl: typing.Callable[..., typing.Any]):
        """Wrap a callable into a Consumer and inject it's return value further
            by calling it every time"""
        cons = self.consumer(cbl)
        # noinspection PyUnusedLocal
        prov: CallableProvider
        if inspect.iscoroutinefunction(cbl):
            prov = FactoryAsyncProvider(cons)
        else:
            prov = FactoryProvider(cons)
        if inspect.isclass(prov.provides):
            for _cls in inspect.getmro(prov.provides):
                self._providers[_cls] = prov
        else:
            self._providers[prov.provides] = prov
        return cons

    def service(self, cls: typing.Type[typing.Any]) -> typing.Type[typing.Any]:
        """Wrap a class to make it's constructor a provider"""
        cls.__init__ = self.consumer(cls.__init__)
        prov = Service(cls)
        for _cls in inspect.getmro(prov.provides):
            self._providers[_cls] = prov
        return cls

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

    def get_provider(self, annotation: typing.Any) -> Provider:
        """Get a provider for annotation"""
        prov = self._providers.get(annotation)
        if not prov:
            # Get provider from parent and cache in self
            if not self._parent:
                raise InjectionError(
                    f"Annotation '{annotation}' has no provider")
            prov = self._providers[annotation] = self._parent.get_provider(annotation)
        return prov


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
