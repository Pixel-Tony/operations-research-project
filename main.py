from intersection import Intersection
from ui import App


if __name__ == '__main__':
    FRAME_RATE = 60
    SIMULATION_SPEED_FACTOR = 15.0
    INTERSECTION_WIDTH = 3
    INTERSECTION_HEIGHT = 3

    model = Intersection(INTERSECTION_WIDTH, INTERSECTION_HEIGHT)

    root = App(model)
    root.title("Traffic Light Sim v0.1")
    root.frame_rate = FRAME_RATE
    root.simulation_speed_factor = SIMULATION_SPEED_FACTOR
    root.geometry('1200x700+300+200')
    root.loop()