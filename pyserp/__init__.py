import collections
import inspect
import functools
import typing


class Injector:
    def __init__(self, package: str = ''):
        self._package = package
        self._services = {}

    def inject(self, cbl: typing.Callable[..., typing.Any]):
        """Mark a callable to have it's arguments auto wired"""
        injected = collections.OrderedDict()
        items: typing.Iterable[
            typing.Tuple[str, inspect.Parameter]
        ] = inspect.signature(cbl).parameters.items()
        for name, param in items:
            provided = self._services.get(param.annotation)
            if provided:
                injected[name] = provided

        # TODO: support positional arguments
        @functools.wraps(cbl)
        def wrapper(**kwargs):
            return cbl(**{**injected, **kwargs})

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
