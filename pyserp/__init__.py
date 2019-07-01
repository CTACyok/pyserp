import functools
import inspect
import typing


class InjectionError(Exception):
    pass


class Injector:
    def __init__(self, name: str = '',
                 parent: typing.Optional['Injector'] = None):
        self._name = name
        self._parent = parent
        self._children: typing.MutableMapping[str, Injector] = {}
        self._services = {}

    def inject(self, cbl: typing.Callable[..., typing.Any]):
        """Mark a callable to have it's arguments auto wired"""
        arguments: typing.Mapping[
            str, inspect.Parameter
        ] = inspect.signature(cbl).parameters

        # TODO: support positional arguments
        @functools.wraps(cbl)
        def wrapper(**kwargs):
            for name, param in arguments.items():
                if name not in kwargs:
                    try:
                        kwargs[name] = self._services[param.annotation]
                    except KeyError as e:
                        raise InjectionError(
                            f"Argument '{name}' is not injected") from e
            return cbl(**kwargs)

        return wrapper

    def provide(self, cbl: typing.Callable[..., typing.Any]):
        """Mark a callable to use it's return value
            as a singleton to inject further"""
        sig = inspect.signature(cbl)
        provided = sig.return_annotation
        injected_cbl = self.inject(cbl)
        self._services[provided] = injected_cbl()

    def get_child(self, name: str) -> 'Injector':
        """Get or create a child-scoped injector
        :param name: comma-separated name to build a scope tree on
        """
        inj = self
        for name_part in name.split('.'):
            child = inj._children.get(name_part)
            if child is None:
                child = inj._children[name_part] = Injector(name_part, inj)
            inj = child
        return inj


def get_injector(name: str) -> Injector:
    """Build scoped injector
    :param name: comma-separated name to build a scope tree on
    """
    return _root.get_child(name)


_root = Injector()

inject = _root.inject
provide = _root.provide
