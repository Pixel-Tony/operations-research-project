from lib import IntersectionSideInfo, TrafficLight, clamp


MIN_GREEN_LIGHT = 9
LIGHT_CYCLE_DUR = 90


class OptimizingTrafficLight(TrafficLight):
    def optimize(self):
        summary_h = self._wait_times[1].sum()
        summary_v = self._wait_times[2].sum()
        self._time_until_optim = 1.5*LIGHT_CYCLE_DUR
        if summary_h == 0:
            self._h_time = MIN_GREEN_LIGHT
            self._v_time = 1.5*LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT
            return

        if summary_v == 0:
            self._v_time = MIN_GREEN_LIGHT
            self._h_time = 1.5*LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT
            return

        s = summary_h + summary_v
        self._time_until_optim = LIGHT_CYCLE_DUR
        self._h_time = clamp(MIN_GREEN_LIGHT, LIGHT_CYCLE_DUR - MIN_GREEN_LIGHT,
                             LIGHT_CYCLE_DUR*summary_h/s)
        self._v_time = LIGHT_CYCLE_DUR - self._h_time