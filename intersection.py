from lib import *


@with_event_handlers_init
class Intersection:
    crosswalk_freed: CrosswalkEvent
    crosswalk_occupied: CrosswalkEvent
    light_changed: Event[dict[IntersectionSideInfo, TrafficLightColor]]
    exit_road_cleared: Event[ConsumerRoad]
    wave_arrived: Event[ProducerRoad]
    car_entered_intersection: Event[tuple[ProducerRoad, ConsumerRoad]]

    def __init__(self, width: int, height: int, light_type: type[TrafficLight],
                 laws: dict[str, list[TrafficFlowLaw]] = None):
        self.width = width
        self.height = height

        if laws is None:
            law = TrafficFlowLaw(
                max_cars=12,
                avg_car_count=3,
                lambda_=1/120,
                min_delay=20,
                max_delay=240,
                min_time_on_intersec=1,
                max_time_on_intersec=5
            )
            laws = {
                side: [law for _ in range(width)]
                for side in 'TB'
            } | {
                side: [law for _ in range(height)]
                for side in 'LR'
            }

        self.roads: dict[str, IntersectionSideInfo] = {
            side: (
                [
                    ProducerRoad(side,
                                 pos,
                                 self.crosswalk_freed,
                                 self.crosswalk_occupied,
                                 laws[side][pos],
                                 self.light_changed)
                    for pos in range(size)
                ], [
                    ConsumerRoad(side, pos,
                                 self.crosswalk_freed,
                                 self.crosswalk_occupied)
                    for pos in range(size)
                ]
            ) for side, size in (
                ('T', width),
                ('R', height),
                ('B', width),
                ('L', height)
            )
        }

        for prods, consumers in self.roads.values():
            [ev.wave_arrived.subscribe(self.wave_arrived)
             or ev.car_entered.subscribe(self.car_entered_intersection)
             for ev in prods]

            [ev.car_consumed.subscribe(self.exit_road_cleared)
             for ev in consumers]

        for law_side in laws.values():
            for law in law_side:
                law.road_info = self.roads

        traffic_light = light_type(roads=self.roads)
        traffic_light.light_changed += self.light_changed
        self.traffic_light = traffic_light

    def tick(self, dt):
        self.traffic_light.tick(dt)
        for side_info in self.roads.values():
            [prod.tick(dt) for prod in side_info[0]]
            [prod.tick(dt) for prod in side_info[1]]
