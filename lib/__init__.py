from typing import Literal
import numpy as np

from .lib_event import *
from .lib_random import *
from .lib_timer import *


PRODUCER_ROAD_PASS_TIMEOUT = 3.0
OPT_LIGHT_AVERAGING_DUR = 50
LIGHT_CYCLE_DUR = 120
OPT_LIGHT_HISTORY_SIZE = 150


def clamp(mn, mx, v): return min(mx, max(mn, v))


def with_event_handlers_init(cls):
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
        self._is_blocked = False
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
        self._consumers_for = {}
        self._min_time_on_intersec = min_time_on_intersec
        self._intersec_span = max_time_on_intersec - min_time_on_intersec

    @property
    def time_to_pass_intersection(self):
        # float in range [min_time_on_intersec; max_time_on_intersec]
        return r.random()*self._intersec_span + self._min_time_on_intersec

    @property
    def road_info(self): raise Exception("Readonly property")

    @road_info.setter
    def road_info(self, value: dict[str, IntersectionSideInfo]):
        def available_roads(i: int, side: str):
            mpp = lambda *xs: dict(map(tuple, xs))
            res = []
            # allow right turn if rightmost
            # can always go up if not rightmost
            # allow left turn if leftmost
            res += [value[mpp('TL', 'BR', 'LB', 'RT')[side]][1][i]] \
                if i == 0 \
                else value[mpp('TB', 'BT', 'LR', 'RL')[side]][1][1:]
            if i == len(value[side][0]) - 1:
                res += [value[mpp('TR', 'BL', 'LT', 'RB')[side]][1][-1]]
            return res

        self._consumers = value
        self._consumers_for = {
            side: {
                road: available_roads(i, road.side)
                for i, road in enumerate(value[side][0])
            }
            for side in value
        }

    def cars(self, side: str, road: 'ProducerRoad') -> list[Car]:
        return [
            Car(r.choice(self._consumers_for[side][road]),
                self.time_to_pass_intersection)
            for _ in range(self._r.binom_dist(self._max_cars, self._mean))
        ]

    @property
    def wave_delay(self):
        value = self._r.exp_dist(self._lambda)
        return clamp(self._min_delay, self._max_delay, value)


@with_event_handlers_init
class TrafficLight(Tickable):
    light_changed: Event[LightChangedEventArgs]

    def __init__(self,
                 *,
                 roads: dict[str, IntersectionSideInfo] = None,
                 other: 'TrafficLight' = None
                 ):
        if roads:
            self.roads = roads
        elif other:
            self.roads = other.roads
        else:
            raise Exception("Either roads or other light must be supplied")

        self._wait_times: np.ndarray = np.full((4, 1), -1)
        self._drop_waiting_amounts()

        self._h_time = LIGHT_CYCLE_DUR/2
        self._v_time = LIGHT_CYCLE_DUR/2
        self._time_until_next_avg = OPT_LIGHT_AVERAGING_DUR
        self._time_until_optim = 60

        self.time_until_switch = 0
        self.states = self.states_iterator()

    def get_samples(self):
        return self._wait_times

    def _drop_waiting_amounts(self):
        self._cur_waiting_amounts = [0, 0]

    def get_durations(self):
        return self._h_time, self._v_time

    def optimize(self): ...

    def tick(self, dt):
        self.time_until_switch -= dt
        if self.time_until_switch <= 0:
            state, time_until_switch = next(self.states)
            # keeping previous negative timing
            self.time_until_switch += time_until_switch
            self.light_changed({side: state[side] for side in self.roads})

        sums = {
            side: sum(road.car_count for road in roads)
            for side, (roads, _) in self.roads.items()
        }
        self._cur_waiting_amounts[0] += dt*(sums['L'] + sums['R'])
        self._cur_waiting_amounts[1] += dt*(sums['T'] + sums['B'])

        self._time_until_optim -= dt
        if self._time_until_optim <= 0:
            self.optimize()
            if self._time_until_optim <= 0:
                self._time_until_optim = 60

        self._time_until_next_avg -= dt
        if self._time_until_next_avg > 0:
            return
        self._time_until_next_avg += OPT_LIGHT_AVERAGING_DUR
        waits = self._wait_times

        X = [waits[0, -1] + dt if waits[0, 0] != -1 else dt][0]
        H, V = self._cur_waiting_amounts
        A = (H + V)/2
        self._drop_waiting_amounts()

        if waits.shape[1] == 1 and waits[0, 0] == -1:
            waits[:, 0] = [X, H, V, A]
        elif waits.shape[1] == OPT_LIGHT_HISTORY_SIZE:
            waits = np.roll(waits, -1, 1)
            waits[:, -1] = [X, H, V, A]
        else:
            waits = np.append(waits, [[X], [H], [V], [A]], 1)
        self._wait_times = waits

    def states_iterator(self) -> tuple[dict[str, TrafficLightColor], float]:
        while True:
            yield ({'T': 'R', 'B': 'R', 'L': 'G', 'R': 'G'}, self._h_time)
            yield ({'T': 'G', 'B': 'G', 'L': 'R', 'R': 'R'}, self._v_time)

@with_event_handlers_init
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
            self._is_blocked = True

    def _on_freed(self, args: IntersectionSideInfo):
        if self in args[1]:
            self._is_blocked = False

    def tick(self, dt: float):
        if not self.is_busy:
            return

        self._duration_left_for_car -= dt
        if self._duration_left_for_car <= 0:
            self._duration_left_for_car = 0
            if self._is_blocked:
                return
            self.upcoming_car = None
            self.car_consumed(self)


@with_event_handlers_init
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
        self._car_on_inters: Car = None
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
            self.cars += self.car_prod_law.cars(self.side, self)
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
            self.timeout = PRODUCER_ROAD_PASS_TIMEOUT
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
