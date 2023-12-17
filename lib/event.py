from typing import TypeVar, Generic, Callable, Any


_T = TypeVar('_T')


class Event(Generic[_T]):
    def __init__(self) -> None:
        self._subs: list[Callable[[_T], Any]] = []

    def __call__(self, event_args: _T) -> None:
        for sub in self._subs:
            sub(event_args)

    def subscribe(self, sub: Callable[[_T], Any]) -> None:
        self._subs.append(sub)

    def __iadd__(self, sub: Callable[[_T], Any]):
        self.subscribe(sub)
        return self

    def unsubscribe(self, sub: Callable[[_T], Any]) -> None:
        self._subs.remove(sub)

    def __isub__(self, sub: Callable[[_T], Any]):
        self.unsubscribe(sub)
        return self
