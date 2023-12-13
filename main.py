import time as t
import random as rnd

from typing import Literal

from lib.base import TrafficLightColor
from lib.event import Event
from lib.random import Random


IntersectionSideInfo = dict[Literal['prod', 'consume'], list['Road']]


class Tickable:
    def tick(self, dt): raise NotImplementedError


class CarProductionLaw:
    pass


class PedestrianProductionLaw:
    pass


# Pedestrian class.
#   Appearing at a road corner, navigates an intersection while trying to reach
#   its destination in a form of some other road corner.
class Pedestrian:
    pass


class Crosswalk:
    def __init__(self, intersection: 'Intersection') -> None:
        self.walkable = False


# Produces and consumes Pedestrians.
#   Some pedestrians can arrive at a corner using a transition point,
#   so only ones that are targeting this corner should be consumed.
class RoadCorner:
    pass


# Base class for roads.
#   A tickable entity that can be free or blocked depending on crosswalk at it.
class Road(Tickable):
    def __init__(self, intersection: 'Intersection') -> None:
        self.is_blocked = True
        intersection.crosswalk_freed += self._on_occupied
        pass

    def _on_occupied(self, data: IntersectionSideInfo): raise NotImplementedError

    def _on_freed(self, data: IntersectionSideInfo): raise NotImplementedError


# Consumes cars.
#   While the crosswalk this road goes through is occupied, current car on the
#   intersection cannot be consumed.
class ConsumerRoad(Road):
    def __init__(self, intersection: 'Intersection', side: str) -> None:
        super().__init__(intersection)
        self.incoming_car = None

    def _on_occupied(self, data: IntersectionSideInfo):
        if self in data['consume']: self.is_blocked = True

    def _on_freed(self, data: IntersectionSideInfo):
        if self in data['consume']: self.is_blocked = False


# Produces cars.
#   While the crosswalk this road goes through is occupied, first car cannot be
#   let to go on the intersection.
class ProducerRoad(Road):
    def __init__(self, intersection: 'Intersection', side: str) -> None:
        super().__init__(intersection)
        self.cars = []

    def _on_occupied(self, data: IntersectionSideInfo):
        if self in data['prod']: self.is_blocked = True

    def _on_freed(self, data: IntersectionSideInfo):
        if self in data['prod']: self.is_blocked = False


# Base traffic light class.
#   Dispatches events indicating light changes depending on implemented mode.
class TrafficLight(Tickable):
    light_changed: Event[dict[IntersectionSideInfo, TrafficLightColor]]
    def __init__(self, roads: dict[str, IntersectionSideInfo]) -> None:
        self.roads = roads
        self.light_changed = Event()


# Intersection model.
#   Main model with purposes of managing entire simulation.
class Intersection:
    crosswalk_occupied: Event[IntersectionSideInfo]
    crosswalk_freed: Event[IntersectionSideInfo]
    traffic_light_changed: Event[dict[list[ProducerRoad]]]

    def __init__(self, width: int, height: int) -> None:
        self.crosswalk_occupied = Event()
        self.corners = TL, TR, BR, BL = [RoadCorner() for _ in range(4)]
        self.roads = {
            side: {
                'prod': [ProducerRoad(self, side) for _ in range(size)],
                'consume': [ConsumerRoad(self, side) for _ in range(size)]
            } for side, size, corners in (
                ('T', width, (TL, TR)),
                ('R', height, (TR, BR)),
                ('B', width, (BR, BL)),
                ('L', height, (BL, TL))
            )
        }
        self.crosswalks = []
        self.traffic_light = TrafficLight(self.roads)

    def tick(self, dt):
        self.traffic_light.tick(dt)

        for item in self.roads.items():
            [pr.tick(dt) for pr in item]
