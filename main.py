from lib import TrafficLight, TrafficFlowLaw
from optimized import OptimizingTrafficLight
from intersection import Intersection
from ui import App

FRAME_RATE = 60
SIMULATION_SPEED_FACTOR = 80.0
INTERSECTION_WIDTH = 2
INTERSECTION_HEIGHT = 3

COMMON_PROPS = dict(min_delay=20, max_delay=240, min_time_on_intersec=1,
                    max_time_on_intersec=5)
laws = [{
    side: [
        TrafficFlowLaw(
            max_cars=15,
            avg_car_count=7,
            lambda_=1/120,
            **COMMON_PROPS
        )
        for _ in range(INTERSECTION_WIDTH)
    ]
    for side in 'TB'
} | {
    side: [TrafficFlowLaw(
        max_cars=10,
        avg_car_count=3,
        lambda_=1/120,
        **COMMON_PROPS
    ) for _ in range(INTERSECTION_HEIGHT)]
    for side in 'LR'
} for _ in range(2)]


model = Intersection(INTERSECTION_WIDTH, INTERSECTION_HEIGHT,
                     OptimizingTrafficLight, laws[0])
model2 = Intersection(INTERSECTION_WIDTH, INTERSECTION_HEIGHT,
                      TrafficLight, laws[1])

root = App(model, model2)
root.title("Traffic Light Sim v0.1")
root.frame_rate = FRAME_RATE
root.simulation_speed_factor = SIMULATION_SPEED_FACTOR
root.geometry('1200x700+300+200')
root.loop()
