from typing import Generic, Callable, Any, Self
from .base import T


class Event(Generic[T]):
    def __init__(self) -> None:
        self._subs: list[Callable[[T], Any]] = []

    def __call__(self, event_args: T) -> None:
        for sub in self._subs:
            sub(event_args)

    def subscribe(self, sub: Callable[[T], Any]) -> None:
        self._subs.append(sub)

    def __iadd__(self, sub: Callable[[T], Any]) -> Self:
        self.subscribe(sub)
        return self
