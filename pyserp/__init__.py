import functools
import inspect
import typing


class InjectionError(Exception):
    pass


class Injector:
    def __init__(self, package: str = ''):
        self._package = package
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


_default = Injector()

inject = _default.inject
provide = _default.provide
