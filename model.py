from dataclasses import dataclass
import sys
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from lib.base import TrafficLightColor
from lib.event import Event
from lib.random import Random


class Tickable:
    def on_tick(self, dt): ...


class ExitRoad(Tickable):
    def __init__(self) -> None:
        self._is_busy = False
        self.cleared_from_car: Event[Self] = Event()

    @property
    def is_busy(self) -> bool:
        return self._is_busy

    def start_consuming_car(self, time: float):
        """`time` - time it takes for car to exit intersection by this road"""
        self._is_busy = True
        self._time_until_clear = time

    def on_tick(self, dt: float):
        if not self.is_busy:
            return

        if self._time_until_clear > 0:
            self._time_until_clear -= dt
            return

        self._time_until_clear = 0
        self._is_busy = False
        self.cleared_from_car(self)

    def __repr__(self) -> str:
        return f"<ExitRoad, is_busy={self.is_busy}>"


@dataclass
class Car:
    destination: ExitRoad


class RoadStatsLaw:
    _r = Random()

    def __init__(self,
                 n: int,
                 p: float,
                 lambda_: float,
                 mn: float,
                 mx: float,
                 exits: list[tuple[float, ExitRoad]]
                 ) -> None:
        self._n = n
        self._p = p

        self._lambda = lambda_
        self._mn = mn
        self._mx = mx
        self._exits = exits

    @property
    def cars(self):
        return [
            Car(self._r.choice(self._exits))
            for _ in range(self._r.binom_dist(self._n, self._p))
        ]

    @property
    def wave_delay(self):
        return min(self._mx, max(self._mn, self._r.exp_dist(self._lambda)))


class EntranceRoad(Tickable):
    def __init__(self,
                 law: RoadStatsLaw,
                 exit_durations: dict[ExitRoad, float]
                 ) -> None:
        self._law = law
        self._delay = law.wave_delay
        self._exit_durations = exit_durations

        self._light: TrafficLightColor = 'R'
        self._cars: list[Car] = []

        self._current_exit: ExitRoad | None = None

        for item in exit_durations:
            item.cleared_from_car += self._on_exit

    def _on_exit(self, road_exit: ExitRoad):
        if self._current_exit is road_exit:
            self._leaving_car = None
            self._cars.pop(0)

    def on_tick(self, dt: float):
        self._update_incoming_cars(dt)
        match self._light:
            case 'G':
                self._tick_while_green_light()
            case 'Y' | 'R':
                return
            case v:
                raise Exception(f"Unexpected light '{v}'")

    def _update_incoming_cars(self, dt: float):
        if self._delay <= 0:
            self._delay = self._law.wave_delay + self._delay
            self._cars.extend(self._law.cars)
        else:
            self._delay -= dt

    def _tick_while_green_light(self):
        if self._current_exit or not self._cars:
            return

        destination = self._cars[0].destination
        if destination.is_busy:
            return

        self._current_exit = destination
        destination.start_consuming_car(self._exit_durations[destination])

    @property
    def car_count(self) -> int:
        return len(self._cars)


@dataclass
class TrafficLightSwitchedArgs:
    color: TrafficLightColor
    side: EntranceRoad


class TrafficLight:
    def __init__(self) -> None:
        self.traffic_light_switched: Event[TrafficLightSwitchedArgs] = Event()


class Model:
    def __init__(self, dt: float) -> None:
        self._dt = dt
        self._exits = [ExitRoad() for _ in range(4)]
        self._exit_times = {a: 3.5 for a in self._exits}
        exit_choice_probs = [(1, road) for road in self._exits]
        self._entrances = [
            EntranceRoad(
                RoadStatsLaw(8, 0.4, 1/50, 20, 180, exit_choice_probs),
                self._exit_times
            )
            for _ in range(4)
        ]

        self._tickables = [
            *self._exits,
            *self._entrances
        ]

    def tick(self) -> None:
        dt = self._dt
        [item.on_tick(dt) for item in self._tickables]
