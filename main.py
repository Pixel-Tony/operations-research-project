from lib import TrafficLight, TrafficFlowLaw
from optimized import OptimizingTrafficLight
from intersection import Intersection
from ui import App

def main():

    FRAME_RATE = 60
    SIMULATION_SPEED_FACTOR = 3.0
    INTERSECTION_WIDTH = 3
    INTERSECTION_HEIGHT = 3

    COMMON_PROPS = dict(min_delay=4, max_delay=200, min_time_on_intersec=0.3,
                        max_time_on_intersec=6)


    def get_laws(): return {
        side: [
            TrafficFlowLaw(
                max_cars=3,
                avg_car_count=2,
                lambda_=1/40/INTERSECTION_WIDTH,
                **COMMON_PROPS
            )
            for _ in range(INTERSECTION_WIDTH)
        ]
        for side in 'TB'
    } | {
        side: [TrafficFlowLaw(
            max_cars=3,
            avg_car_count=1,
            lambda_=1/60/INTERSECTION_HEIGHT,
            **COMMON_PROPS
        ) for _ in range(INTERSECTION_HEIGHT)]
        for side in 'LR'
    }


    model = Intersection(INTERSECTION_WIDTH, INTERSECTION_HEIGHT,
                        OptimizingTrafficLight, get_laws())
    model2 = Intersection(INTERSECTION_WIDTH, INTERSECTION_HEIGHT,
                        TrafficLight, get_laws())

    root = App([model, model2], labels=(
        'Середній сумарний час у світлофора з оптимізацією',
        'Середній сумарний час у звичайного світлофора'
    ))
    root.title("Traffic Light Sim v0.1")
    root.frame_rate = FRAME_RATE
    root.simulation_speed_factor = SIMULATION_SPEED_FACTOR
    root.geometry('1200x700+300+200')
    root.loop()


if __name__ == '__main__':
    main()