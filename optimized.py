from lib import *
from lib import IntersectionSideInfo, TrafficLight


MIN_GREEN_LIGHT = 5
LIGHT_CYCLE_DUR = 20


class OptimizingTrafficLight(TrafficLight):
    def __init__(self, *, roads: dict[str, IntersectionSideInfo] = None, other: TrafficLight = None):
        super().__init__(roads=roads, other=other)
        self._h_time = 100
        self._v_time = 100
    def optimize(self):
        print("Recalculating...")
        summary_h = self._wait_times[1].sum()
        summary_v = self._wait_times[2].sum()
        if summary_h == 0:
            self._h_time = MIN_GREEN_LIGHT
            self._v_time = 2*LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT
            self._time_until_optim = 2.5*LIGHT_CYCLE_DUR
            return

        if summary_v == 0:
            self._v_time = MIN_GREEN_LIGHT
            self._h_time = 2*LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT
            self._time_until_optim = 2.5*LIGHT_CYCLE_DUR
            return

        s = summary_h + summary_v

        if summary_h >= 5*summary_v:
            self._h_time = 1.5*LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT
            self._v_time = MIN_GREEN_LIGHT
            self._time_until_optim = 2*LIGHT_CYCLE_DUR
            return
        if summary_v >= 5*summary_h:
            self._h_time = MIN_GREEN_LIGHT
            self._v_time = 1.5*LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT
            self._time_until_optim = 2*LIGHT_CYCLE_DUR
            return

        self._h_time = clamp(MIN_GREEN_LIGHT, LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT,
                             LIGHT_CYCLE_DUR*summary_h/s)
        self._v_time = LIGHT_CYCLE_DUR - self._h_time
        self._time_until_optim = OPT_LIGHT_OPTIMIZATION_STEP_DELAY