from tkinter import Button, Tk, Label, Frame, Canvas

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.axes import Axes

from intersection import Intersection
from lib import Timer, ProducerRoad, ConsumerRoad


FONT = "Helvetica 14"

ROAD_WIDTH = 48
ROAD_COLOR = '#203040'
ROAD_MARK_YELLOW = '#dd4'
ROAD_PAD_XY = 60

ARROW_WIDTH = 3

CROSSWALK_WIDTH = 26
CROSSWALK_GAP = 6
CROSSWALK_COLOR = '#ccc'

GRAPH_UPDATE_INTERVAL = 3
GRAPH_HISTORY_SIZE = 80


class App(Tk):
    def __init__(self, models: list[Intersection], labels: list[str]):
        super().__init__()
        self.model = models[0]
        self.models = models
        self.labels = labels

        self.protocol('WM_DELETE_WINDOW', self.close)
        self.resizable(False, False)
        self.running = True
        self._draw_ui()
        self._frame_rate = 60

        self._plots_info = None
        self._graph_update_delay = GRAPH_UPDATE_INTERVAL

        self.timer = Timer(1/self._frame_rate)
        self._simulation_speed_factor = 1
        for prods, _ in self.model.roads.values():
            for road in prods:
                road.wave_arrived += self._on_wave_arrived

        self.model.light_changed += self._on_traffic_light_change
        self.model.car_entered_intersection += self._on_car_entered_inters
        self.model.exit_road_cleared += self._on_exit_cleared
        self.arrows: dict[
            ConsumerRoad, (ProducerRoad, int, tuple[int, ...], float)
        ] = {}

    def _on_car_entered_inters(self, args: tuple[ProducerRoad, ConsumerRoad]):
        prod, cons = args

        label = self.car_count_labels[prod.side][prod]
        label.config(text=str(prod.car_count))

        pside, p_ind = [
            (side, prods.index(prod))
            for side, (prods, _) in self.model.roads.items()
            if prod in prods
        ][0]
        cside, c_ind = [
            (side, conss.index(cons))
            for side, (_, conss) in self.model.roads.items()
            if cons in conss
        ][0]
        line_id, coords = self._add_arrow(pside, p_ind, cside, c_ind)
        self.arrows[cons] = (prod, line_id, coords, cons.consumption_time)

    def _on_exit_cleared(self, end: ConsumerRoad):
        self.canvas.delete(self.arrows.pop(end)[1])

    def _on_traffic_light_change(self, current_state: dict):
        for side, color in current_state.items():
            self.canvas.itemconfig(self.light_lens[side],
                                   fill={'R': '#ff2222', 'G': '#22ff22'}[color])

    def _on_wave_arrived(self, road: ProducerRoad):
        label = self.car_count_labels[road.side][road]
        label.config(text=str(road.car_count))

    def _draw_ui(self):
        def rectangle(x, y, w, h, **kwgs):
            return canvas.create_rectangle(x, y, x + w, y + h, **kwgs)

        def make_graph(parent, x, y, width, height):
            fig = Figure(figsize=(width/100 - 0.02, height / 100 - 0.02),
                         dpi=100,
                         linewidth=0.1,
                         edgecolor='black')
            canvas = FigureCanvasTkAgg(fig, parent)
            canvas.draw()
            canvas.get_tk_widget().place(x=x, y=y, width=width, height=height)
            ax = Axes(fig, 1, 1, 1)
            fig.add_axes(ax)
            ax.set_xlabel('Час з початку симуляції, с')
            ax.set_ylabel('Час, с')
            return fig, ax

        def make_decorations():
            # Road plates: horizontal, vertical
            canvas.create_rectangle(
                0, ROAD_PAD_XY, 2*X_MID + 1, Y_MID*2 - ROAD_PAD_XY + 1,
                fill=ROAD_COLOR, width=0
            )
            canvas.create_rectangle(
                ROAD_PAD_XY, 0, 2*X_MID - ROAD_PAD_XY + 1, 2*Y_MID + 1,
                fill=ROAD_COLOR, width=0
            )

            # Yellow lines: horizontal (left, right), vertical (top, bottom)
            LINE_CFG = dict(fill=ROAD_MARK_YELLOW, width=2)
            canvas.create_line(0, Y_MID, ROAD_PAD_XY, Y_MID,
                               **LINE_CFG)
            canvas.create_line(2*X_MID - ROAD_PAD_XY, Y_MID, 2*X_MID + 1, Y_MID,
                               **LINE_CFG)
            canvas.create_line(X_MID, 0, X_MID, ROAD_PAD_XY,
                               **LINE_CFG)
            canvas.create_line(X_MID, 2*Y_MID - ROAD_PAD_XY, X_MID, 2*Y_MID + 1,
                               **LINE_CFG)

            # horizontal lane delimiter lines
            LANE_DELIM_LENGTH = ROAD_PAD_XY - CROSSWALK_WIDTH - 5
            [
                canvas.create_line(cur_x,
                                   cur_y,
                                   cur_x + LANE_DELIM_LENGTH,
                                   cur_y,
                                   fill='white', width=1)
                for count in range(1, ROADS_H)
                for cur_x in (0, 2*X_MID - LANE_DELIM_LENGTH)
                for cur_y in (count*(ROAD_WIDTH + 1) - 1 + ROAD_PAD_XY,
                              count*(ROAD_WIDTH + 1) - 1 + Y_MID)
            ]
            # vertical lane delimiter lines
            [
                canvas.create_line(cur_x,
                                   cur_y,
                                   cur_x,
                                   cur_y + LANE_DELIM_LENGTH,
                                   fill='white', width=0)
                for count in range(1, ROADS_W)
                for cur_y in (0, 2*Y_MID - LANE_DELIM_LENGTH)
                for cur_x in (count*(ROAD_WIDTH + 1) - 1 + ROAD_PAD_XY,
                              count*(ROAD_WIDTH + 1) - 1 + X_MID)
            ]

        ROADS_W, ROADS_H = self.model.width, self.model.height
        X_MID = ROAD_PAD_XY + ROADS_W*(ROAD_WIDTH + 1) - 1
        Y_MID = ROAD_PAD_XY + ROADS_H*(ROAD_WIDTH + 1) - 1

        CANVAS_PAD_Y = 80
        self.canvas_frame = Frame(self)
        self.canvas_frame.place(x=80, y=CANVAS_PAD_Y, width=500, height=500)

        canvas = Canvas(self.canvas_frame)
        self.canvas = canvas
        canvas.place(width=500, height=500)

        self.graph_frame = Frame(self)
        self.graph_frame.place(x=550, y=50, width=600, height=500)
        self.figure, self.graph = make_graph(self.graph_frame, 0, 0, 600, 500)

        make_decorations()

        def make_crosswalks():
            CROSSWALK_CFG = dict(fill=CROSSWALK_COLOR, width=0)

            def p_left(i, line_num): return ROAD_PAD_XY + i*(ROAD_WIDTH + 1)\
                + CROSSWALK_GAP//2 + 2*line_num*CROSSWALK_GAP
            def p_top(i, line_num): return ROAD_PAD_XY + i*(ROAD_WIDTH + 1)\
                + CROSSWALK_GAP//2 + 2*line_num*CROSSWALK_GAP

            vertical = [
                [
                    rectangle(cur_left, cur_top,
                              CROSSWALK_GAP, CROSSWALK_WIDTH,
                              **CROSSWALK_CFG)
                    for cur_top in (ROAD_PAD_XY - CROSSWALK_WIDTH,
                                    2*Y_MID - ROAD_PAD_XY)
                ]
                for i in range(ROADS_W)
                for line_n in range(ROAD_WIDTH // (2*CROSSWALK_GAP))
                for cur_left in (p_left(i, line_n),
                                 2*X_MID - p_left(i, line_n) - CROSSWALK_GAP)
            ]
            horizontal = [
                [
                    rectangle(cur_left, cur_top,
                              CROSSWALK_WIDTH, CROSSWALK_GAP,
                              **CROSSWALK_CFG)
                    for cur_left in (ROAD_PAD_XY - CROSSWALK_WIDTH,
                                     2*X_MID - ROAD_PAD_XY)
                ]
                for line_n in range(ROAD_WIDTH // (2*CROSSWALK_GAP))
                for i in range(ROADS_H)
                for cur_top in (p_top(i, line_n),
                                2*Y_MID - p_top(i, line_n) - CROSSWALK_GAP)
            ]
            top, bottom = [*zip(*vertical)]
            left, right = [*zip(*horizontal)]
            return {
                side: cw
                for side, cw in zip('TRBL', (top, right, bottom, left))
            }

        # Crosswalks
        self.crosswalk_sprites = make_crosswalks()

        # Car count labels
        self.car_count_labels = {
            side: {
                road: Label(self, text='0', justify='center', font=FONT)
                for road in self.model.roads[side][0]
            }
            for side in self.model.roads
        }
        CAR_COUNT_LABEL_CFG = dict(width=ROAD_WIDTH, height=30)
        for i, lbl in enumerate(self.car_count_labels['T'].values()):
            lbl.place(x=80 + ROAD_PAD_XY + (ROAD_WIDTH + 1)*i,
                      y=CANVAS_PAD_Y - 30,
                      **CAR_COUNT_LABEL_CFG)
        for i, lbl in enumerate(self.car_count_labels['B'].values()):
            lbl.place(x=80 + 2*X_MID - ROAD_PAD_XY - (ROAD_WIDTH + 1)*(i + 1),
                      y=CANVAS_PAD_Y + 1 + 2*Y_MID,
                      **CAR_COUNT_LABEL_CFG)
        for i, lbl in enumerate(self.car_count_labels['L'].values()):
            lbl.place(x=30,
                      y=CANVAS_PAD_Y + 2*Y_MID - ROAD_PAD_XY -
                      (ROAD_WIDTH + 1)*(i + 1) + (ROAD_WIDTH - 30)//2,
                      **CAR_COUNT_LABEL_CFG)
        for i, lbl in enumerate(self.car_count_labels['R'].values()):
            lbl.place(x=81 + 2*X_MID,
                      y=CANVAS_PAD_Y + ROAD_PAD_XY +
                      (ROAD_WIDTH + 1)*i + (ROAD_WIDTH - 30)//2,
                      **CAR_COUNT_LABEL_CFG)

        def make_traffic_light():
            HALF_TLB_SIZE = 10
            LWIDTH = 6

            top = canvas.create_oval(X_MID - HALF_TLB_SIZE + 1,
                                     Y_MID - HALF_TLB_SIZE - LWIDTH,
                                     X_MID + HALF_TLB_SIZE - 1,
                                     Y_MID - HALF_TLB_SIZE + LWIDTH,
                                     width=0)
            right = canvas.create_oval(X_MID + HALF_TLB_SIZE - LWIDTH,
                                       Y_MID - HALF_TLB_SIZE + 1,
                                       X_MID + HALF_TLB_SIZE + LWIDTH,
                                       Y_MID + HALF_TLB_SIZE - 1,
                                       width=0)
            bottom = canvas.create_oval(X_MID - HALF_TLB_SIZE + 1,
                                        Y_MID + HALF_TLB_SIZE - LWIDTH,
                                        X_MID + HALF_TLB_SIZE - 1,
                                        Y_MID + HALF_TLB_SIZE + LWIDTH,
                                        width=0)
            left = canvas.create_oval(X_MID - HALF_TLB_SIZE - LWIDTH,
                                      Y_MID - HALF_TLB_SIZE + 1,
                                      X_MID - HALF_TLB_SIZE + LWIDTH,
                                      Y_MID + HALF_TLB_SIZE - 1,
                                      width=0)

            X, Y, A = X_MID, Y_MID, HALF_TLB_SIZE
            canvas.create_rectangle(X - A, Y - A, X + A + 1, Y + A + 1,
                                    fill='#aaa', width=0)
            return top, right, bottom, left

        # Traffic light itself
        self.light_lens = {
            side: i
            for side, i in zip('TRBL', make_traffic_light())
        }

        Button(self, text='<<', command=self._sim_speed_decrease, font=FONT)\
            .place(x=580, y=5, width=40, height=40)
        Button(self, text='>>', command=self._sim_speed_increase, font=FONT)\
            .place(x=640, y=5, width=40, height=40)

        self.speed_label = Label(self, font=FONT)
        self.speed_label.place(x=700, y=5, height=40, width=250)

    def _sim_speed_increase(self):
        cur = self.simulation_speed_factor
        self.simulation_speed_factor = min(cur*2, 5*self.frame_rate)

    def _sim_speed_decrease(self):
        cur = self.simulation_speed_factor
        self.simulation_speed_factor = max(cur//2, 1)

    def _add_arrow(self, pside: str, p_ind: int, cside: str, c_ind: int):
        ROADS_W, ROADS_H = self.model.width, self.model.height
        X_MID = ROAD_PAD_XY + ROADS_W*(ROAD_WIDTH + 1) - 1
        Y_MID = ROAD_PAD_XY + ROADS_H*(ROAD_WIDTH + 1) - 1

        P_SHIFT = (ROAD_WIDTH + 1)*(p_ind + 1) - ROAD_WIDTH // 2
        C_SHIFT = (ROAD_WIDTH + 1)*(c_ind + 1) - ROAD_WIDTH // 2

        x, y, x1, y1 = [ROAD_PAD_XY for _ in '1234']
        match pside:
            case 'T':
                x += P_SHIFT
            case 'R':
                x = 2*X_MID - x
                y += P_SHIFT
            case 'B':
                x = 2*X_MID - x - P_SHIFT
                y = 2*Y_MID - y
            case 'L':
                y = 2*Y_MID - y - P_SHIFT
        match cside:
            case 'T':
                x1 = 2*X_MID - x1 - C_SHIFT
            case 'R':
                x1 = 2*X_MID - x1
                y1 = 2*Y_MID - y1 - C_SHIFT
            case 'B':
                x1 += C_SHIFT
                y1 = 2*Y_MID - y1
            case 'L':
                y1 += C_SHIFT

        return (self.canvas.create_line(
            x, y, x1, y1, arrow='last', width=ARROW_WIDTH, fill='#ff8800'),
            (x, y, x1, y1)
        )

    @property
    def simulation_speed_factor(self):
        return self._simulation_speed_factor

    @simulation_speed_factor.setter
    def simulation_speed_factor(self, value):
        self._simulation_speed_factor = value
        self.speed_label.config(text=f"Швидкість симуляції: {value}x")

    @property
    def frame_rate(self):
        return self._frame_rate

    @frame_rate.setter
    def frame_rate(self, value):
        self._frame_rate = value
        self.timer.delay = 1/value

    def close(self):
        self.running = False

    def update(self, dt) -> None:
        super().update()
        for exit, (_, arrow_id, (x, y, x1, y1), dur) in self.arrows.items():
            t = exit.consumption_time/dur
            coords = (x*t + x1*(1-t), y*t + y1*(1-t), x1, y1)
            self.canvas.coords(arrow_id, coords)

        self._graph_update_delay -= dt
        if self._graph_update_delay > 0:
            return
        self._graph_update_delay += GRAPH_UPDATE_INTERVAL
        self._update_graph()

    def _update_graph(self):
        for model in self.models:
            coords = model.traffic_light.get_samples()
            self._plots_info[model].set_data(coords[0], coords[3])

        self.graph.set_xlim(coords[0, 0] - 2, coords[0, -1] + 2)
        self.graph.set_ylim(-2, max(m.traffic_light.get_samples()[1:3].max()
                            for m in self.models))
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    def loop(self):
        self._plots_info = {
            model: self.graph.plot(coords[0], coords[3], label=label)[0]
            for (model, label) in zip(self.models, self.labels)
            for coords in [model.traffic_light.get_samples()]
        }
        self.graph.legend()

        while self.running:
            with self.timer:
                model_tick = self._simulation_speed_factor/self._frame_rate
                [m.tick(model_tick) for m in self.models]
                self.update(model_tick)
                self.update_idletasks()
