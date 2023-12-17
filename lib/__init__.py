from typing import Literal

from .Event import *
from .Random import *
from .Timer import *


def auto_events(cls):
    names = [
        name
        for name, typ in cls.__annotations__.items()
        if typ.__origin__ is Event
    ]
    def __init__(s):
        [setattr(s, name, Event()) for name in names]

    _old_init = getattr(cls, '__init__')
    def new_init(s, *args, **kwgs):
        __init__(s)
        _old_init(s, *args, **kwgs)

    setattr(cls, '__init__', new_init)
    return cls


class Tickable:
    def tick(self, dt: float): raise NotImplementedError


TrafficLightColor = Literal['R', 'Y', 'G']
LightChangedEventArgs = dict[str, TrafficLightColor]
IntersectionSideInfo = tuple[list['ProducerRoad'], list['ConsumerRoad']]
CrosswalkEvent = Event[IntersectionSideInfo]


class Road(Tickable):
    def __init__(self,
                 crosswalk_freed: CrosswalkEvent,
                 crosswalk_occupied: CrosswalkEvent
                 ) -> None:
        self._is_blocked = True
        crosswalk_freed += self._on_freed
        crosswalk_occupied += self._on_occupied

    def _on_occupied(self, data: IntersectionSideInfo):
        raise NotImplementedError

    def _on_freed(self, data: IntersectionSideInfo):
        raise NotImplementedError


class Car:
    __slots__ = ['destination', '_time_to_pass']
    destination: 'ConsumerRoad'

    def __init__(self, destination: Road, time_to_pass: float) -> None:
        self.destination = destination
        self._time_to_pass = time_to_pass

    def get_intersection_pass_duration(self):
        return self._time_to_pass


class TrafficFlowLaw:
    _r = Random()

    def __init__(self,
                 max_cars: int,
                 avg_car_count: float,
                 lambda_: float,
                 min_delay: float,
                 max_delay: float,
                 min_time_on_intersec: float,
                 max_time_on_intersec: float,
                 ) -> None:
        self._max_cars = max_cars
        self._mean = avg_car_count / max_cars

        self._lambda = lambda_
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._consumers: list[ConsumerRoad] = []
        self._min_time_on_intersec = min_time_on_intersec
        self._intersec_span = max_time_on_intersec - min_time_on_intersec

    @property
    def time_to_pass_intersection(self):
        # float in range [min_time_on_intersec; max_time_on_intersec]
        return r.random()*self._intersec_span + self._min_time_on_intersec

    @property
    def consumer_roads(self):
        return self._consumers

    @consumer_roads.setter
    def consumer_roads(self, value: dict[str, tuple[float, 'ConsumerRoad']]):
        self._consumers = [
            road for roads in value.values()
            for road in roads
        ]
        self._consumers_without = {
            side: [
            road
            for road in self._consumers
            if road not in value[side]
            ]
            for side in value
        }

    def cars(self, exclude: str) -> list[Car]:
        return [
            Car(self._r.choice(self._consumers_without[exclude]),
                self.time_to_pass_intersection)
            for _ in range(self._r.binom_dist(self._max_cars, self._mean))
        ]

    @property
    def wave_delay(self):
        return self._clamp(self._r.exp_dist(self._lambda))

    def _clamp(self, v):
        return min(self._max_delay, max(v, self._min_delay))


@auto_events
class TrafficLight(Tickable):
    light_changed: Event[LightChangedEventArgs]

    def __init__(self, roads: dict[str, IntersectionSideInfo]) -> None:
        self.roads = roads
        self.time_until_switch = 0
        self.states = self.states_iterator()

    def tick(self, dt):
        if self.time_until_switch <= 0:
            state, time_until_switch = next(self.states)
            # keeping previous negative timing
            self.time_until_switch += time_until_switch - dt
            self.light_changed({side: state[side] for side in self.roads})

        self.time_until_switch -= dt

    def states_iterator(self) -> tuple[dict[str, TrafficLightColor], float]:
        while True:
            yield ({'T': 'R', 'B': 'R', 'L': 'G', 'R': 'G'}, 30)
            yield ({'T': 'G', 'B': 'G', 'L': 'R', 'R': 'R'}, 30)


@auto_events
class ConsumerRoad(Road):
    car_consumed: Event['ConsumerRoad']

    def __init__(self,
                 side: str,
                 pos: int,
                 crosswalk_freed: CrosswalkEvent,
                 crosswalk_occupied: CrosswalkEvent
                 ):
        super().__init__(crosswalk_freed, crosswalk_occupied)
        self.side = side
        self.pos = pos
        self.upcoming_car: Car = None
        self._duration_left_for_car = 0.0

    @property
    def is_busy(self):
        return self.upcoming_car is not None

    @property
    def consumption_time(self):
        return self._duration_left_for_car

    def accept(self, car: Car):
        self.upcoming_car = car
        self._duration_left_for_car = car.get_intersection_pass_duration()

    def _on_occupied(self, args: IntersectionSideInfo):
        if self in args[1]:
            self.is_blocked = True

    def _on_freed(self, args: IntersectionSideInfo):
        if self in args[1]:
            self.is_blocked = False

    def tick(self, dt: float):
        if not self.is_busy:
            return

        self._duration_left_for_car -= dt
        if self._duration_left_for_car <= 0:
            self.upcoming_car = None
            self.car_consumed(self)


@auto_events
class ProducerRoad(Road):
    wave_arrived: Event['ProducerRoad']
    car_entered: Event[tuple['ProducerRoad', 'ConsumerRoad']]

    def __init__(self,
                 side: str,
                 pos: int,
                 crosswalk_freed: CrosswalkEvent,
                 crosswalk_occupied: CrosswalkEvent,
                 car_production_law: TrafficFlowLaw,
                 traffic_light_changed: Event[LightChangedEventArgs]
                 ):

        super().__init__(crosswalk_freed, crosswalk_occupied)
        self.side = side
        self.pos = pos
        self.timeout = 0
        traffic_light_changed += self._on_traffic_light_changed

        self.car_prod_law = car_production_law

        self.cars: list[Car] = []
        self._has_car_on_intersection = False
        self._t_until_wave = car_production_law.wave_delay

    def _on_traffic_light_changed(self, args: LightChangedEventArgs):
        self.current_light = args[self.side]

    def tick(self, dt: float):
        self._update_incoming_cars(dt)
        match self.current_light:
            case 'R' | 'Y':
                pass
            case 'G':
                self._green_light_tick(dt)
            case v: raise Exception(f"Unexpected light '{v}'")

    def _update_incoming_cars(self, dt: float):
        if self._t_until_wave <= 0:
            self._t_until_wave += self.car_prod_law.wave_delay
            self.cars += self.car_prod_law.cars(self.side)
            self.wave_arrived(self)
        self._t_until_wave -= dt

    def _green_light_tick(self, dt: float):
        if not self.cars:
            return

        self.timeout -= dt
        if self.timeout > 0:
            return

        destination = self.cars[0].destination
        if not destination.is_busy:
            destination.accept(self.cars.pop(0))
            self.timeout = 2
            self.car_entered((self, destination))

    @property
    def car_count(self):
        return len(self.cars)

    def _on_occupied(self, data: IntersectionSideInfo):
        if self in data[0]:
            self._is_blocked = True

    def _on_freed(self, data: IntersectionSideInfo):
        if self in data[0]:
            self._is_blocked = False
