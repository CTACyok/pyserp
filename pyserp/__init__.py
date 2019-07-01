import functools
import inspect
import typing


class InjectionError(Exception):
    pass


_CR_TV = typing.TypeVar('_CR_TV')


class Consumer:
    """Wrapper for callable that substitutes it's missing arguments"""

    def __init__(self, cbl: typing.Callable[..., _CR_TV], inj: 'Injector'):
        self._callable = cbl
        self._injector = inj
        self._signature = inspect.signature(self._callable)
        self._parameters: typing.Mapping[
            str, inspect.Parameter] = self._signature.parameters
        functools.update_wrapper(self, cbl)

    def __call__(self, **kwargs) -> _CR_TV:
        # TODO: support positional arguments
        for name, param in self._parameters.items():
            if name not in kwargs:
                kwargs[name] = self._injector.get_provided(param.annotation)
        return self._callable(**kwargs)


_PR_TV = typing.TypeVar('_PR_TV')


class Provider:
    """An abstract provider"""

    def __init__(self, cbl: typing.Callable[[], _PR_TV]):
        self._callable = cbl
        # Calls for `inspect.signature` are cached
        self._signature = inspect.signature(self._callable)
        self._return_annotation = self._signature.return_annotation

    @property
    def provides(self) -> typing.Any:
        return self._return_annotation

    def provide(self) -> _PR_TV:
        raise NotImplementedError()


class SingletonProvider(Provider):
    """Provider of the same object for every call"""

    def __init__(self, cbl: typing.Callable[[], _PR_TV]):
        super().__init__(cbl)
        self._provided = self._callable()

    def provide(self) -> _PR_TV:
        return self._provided


class FactoryProvider(Provider):
    """Provider of a new object for every call"""

    def provide(self) -> _PR_TV:
        return self._callable()


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
        return Consumer(cbl, self)

    def provider(self, cbl: typing.Callable[..., typing.Any]) -> Consumer:
        """Wrap a callable into a Consumer and inject it's return value further
            as a singleton"""
        cons = self.consumer(cbl)
        prov = SingletonProvider(cons)
        self._providers[prov.provides] = prov
        return cons

    def factory(self, cbl: typing.Callable[..., typing.Any]) -> Consumer:
        """Wrap a callable into a Consumer and inject it's return value further
            by calling it every time"""
        cons = self.consumer(cbl)
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
