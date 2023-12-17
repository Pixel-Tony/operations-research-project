from lib import *





@auto_events
class Intersection:
    crosswalk_freed: CrosswalkEvent
    crosswalk_occupied: CrosswalkEvent
    light_changed: Event[dict[IntersectionSideInfo, TrafficLightColor]]
    exit_road_cleared: Event[ConsumerRoad]
    wave_arrived: Event[ProducerRoad]
    car_entered_intersection: Event[tuple[ProducerRoad, ConsumerRoad]]

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        # self.corners =
        TL, TR, BR, BL = [None for _ in range(4)]

        self._production_law = TrafficFlowLaw(
            max_cars=12,
            avg_car_count=3,
            lambda_=1/80,
            min_delay=20,
            max_delay=240,
            min_time_on_intersec=2,
            max_time_on_intersec=5
        )

        self.roads: dict[str, tuple[list[ProducerRoad], list[ConsumerRoad]]] = {
            side: (
                [
                    ProducerRoad(side,
                                 pos,
                                 self.crosswalk_freed,
                                 self.crosswalk_occupied,
                                 self._production_law,
                                 self.light_changed)
                    for pos in range(size)
                ], [
                    ConsumerRoad(side, pos,
                                 self.crosswalk_freed,
                                 self.crosswalk_occupied)
                    for pos in range(size)
                ]
            ) for side, size, corners in (
                ('T', width, (TL, TR)),
                ('R', height, (TR, BR)),
                ('B', width, (BR, BL)),
                ('L', height, (BL, TL))
            )
        }

        for prods, consumers in self.roads.values():
            [ev.wave_arrived.subscribe(self.wave_arrived)
             or ev.car_entered.subscribe(self.car_entered_intersection)
             for ev in prods]

            [ev.car_consumed.subscribe(self.exit_road_cleared)
             for ev in consumers]

        self._production_law.consumer_roads = {
            side: [
                (i*i, road)
                for i, road in enumerate(consumers)
            ]
            for side, (_, consumers) in self.roads.items()
        }

        traffic_light = TrafficLight(self.roads)
        traffic_light.light_changed += self.light_changed
        self.traffic_light = traffic_light

    @property
    def production_law(self):
        return self._production_law

    def tick(self, dt):
        self.traffic_light.tick(dt)
        for side_info in self.roads.values():
            [prod.tick(dt) for prod in side_info[0]]
            [prod.tick(dt) for prod in side_info[1]]
