import sys

from typing import Generic, Callable, Any, Self, TypeVar, Literal
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


T = TypeVar('T')


TrafficLightColor = Literal['G', 'Y', 'R']


class Event(Generic[T]):
    def __call__(self, event_args: T): ...
    def subscribe(self, sub: Callable[[T], Any]): ...
    def __iadd__(self, sub: Callable[[T], Any]) -> Self: ...


class Random:
    def exp_dist(self, lambda_: float) -> float: ...
    def binom_dist(self, n: int, p: float) -> int: ...
    def choice(self, pairs: list[tuple[float, T]]) -> T: ...


class ExitRoad:
    cleared_from_car: Event[Self]
    @property
    def is_busy(self) -> bool: ...
    def start_consuming_car(self, time: float): ...
    def on_tick(self, dt: float): ...


class Car:
    destination: ExitRoad


class RoadStatsLaw:
    @property
    def cars(self) -> list[Car]: ...
    @property
    def wave_delay(self) -> float: ...


class EntranceRoad:
    def on_tick(self, dt: float): ...
    @property
    def car_count(self) -> int: ...


class TrafficLightSwitchedArgs:
    color: TrafficLightColor
    side: EntranceRoad


class TrafficLight:
    traffic_light_switched: Event[TrafficLightSwitchedArgs]


class Model:
    def tick(self): ...
