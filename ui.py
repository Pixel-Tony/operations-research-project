from tkinter import Tk, Label, Frame, Canvas

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

CROSSWALK_WIDTH = 26
CROSSWALK_GAP = 6
CROSSWALK_COLOR = '#ccc'


class App(Tk):
    def __init__(self, model: Intersection):
        super().__init__()
        self.model = model

        self.protocol('WM_DELETE_WINDOW', self.close)
        self.resizable(False, False)
        self.running = True
        self._draw_ui()
        self._frame_rate = 60

        self.timer = Timer(1/self._frame_rate)
        self._simulation_speed_factor = 1
        for prods, _ in self.model.roads.values():
            for road in prods:
                road.wave_arrived += self._on_wave_arrived

        self.model.light_changed += self._on_traffic_light_change
        self.model.car_entered_intersection += self._on_car_entered_inters
        self.model.exit_road_cleared += self._on_exit_cleared
        self.arrows: dict[ConsumerRoad, (ProducerRoad, int, float)] = {}


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
        line_id = self._add_line(pside, p_ind, cside, c_ind)
        self.arrows[cons] = (prod, line_id)

    def _on_exit_cleared(self, end: ConsumerRoad):
        (_, ind) = self.arrows.pop(end)
        self.canvas.delete(ind)

    def _on_traffic_light_change(self, current_state: dict):
        for side, color in current_state.items():
            self.canvas.itemconfig(self.light_lens[side],
                                   fill={'R': 'red', 'G': 'green'}[color])

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
            return ax

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

        self.canvas_frame = Frame(self)
        self.canvas_frame.place(x=80, y=80, width=500, height=500)

        canvas = Canvas(self.canvas_frame)
        self.canvas = canvas
        canvas.place(width=500, height=500)

        self.graph_frame = Frame(self)
        self.graph_frame.place(x=550, y=50, width=600, height=400)
        self.graph = make_graph(self.graph_frame, 0, 0, 600, 400)

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
                      y=50,
                      **CAR_COUNT_LABEL_CFG)
        for i, lbl in enumerate(self.car_count_labels['B'].values()):
            lbl.place(x=80 + 2*X_MID - ROAD_PAD_XY - (ROAD_WIDTH + 1)*(i + 1),
                      y=81 + 2*Y_MID,
                      **CAR_COUNT_LABEL_CFG)
        for i, lbl in enumerate(self.car_count_labels['L'].values()):
            lbl.place(x=30,
                      y=80 + 2*Y_MID - ROAD_PAD_XY - (ROAD_WIDTH + 1)*(i + 1) + (ROAD_WIDTH - 30)//2,
                      **CAR_COUNT_LABEL_CFG)
        for i, lbl in enumerate(self.car_count_labels['R'].values()):
            lbl.place(x=81 + 2*X_MID,
                      y=80 + ROAD_PAD_XY +
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

    def _add_line(self, pside: str, p_ind: int, cside: str, c_ind: int):
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

        return self.canvas.create_line(x, y, x1, y1,
                                       arrow='last', width=2, fill='red')

    @property
    def simulation_speed_factor(self):
        return self._simulation_speed_factor

    @simulation_speed_factor.setter
    def simulation_speed_factor(self, value):
        self._simulation_speed_factor = value

    @property
    def frame_rate(self):
        return self._frame_rate

    @frame_rate.setter
    def frame_rate(self, value):
        self._frame_rate = value
        self.timer.delay = 1/value

    def close(self):
        self.running = False

    def loop(self):
        while self.running:
            with self.timer:
                self.update()
                self.update_idletasks()
                self.model.tick(self._simulation_speed_factor/self._frame_rate)


def col_interp(c1: str, c2: str, t: float):
    assert len(c1) == len(c2) == 6 and 0 <= t <= 1
    hxi = lambda i: '0123456789abcdef'.index(i)
    fromhex = lambda c: hxi(c) if not c[1:] else 16*hxi(c[0]) + fromhex(c[1:])
    totup = lambda c: (fromhex(c[:2]), fromhex(c[2:4]), fromhex(c[4:]))
    c1, c2 = totup(c1.lower()), totup(c2.lower())
    mid = [min(256, int(a*t + b*(1 - t))) for a, b in zip(c1, c2)]
    return hex(((mid[0]*256) + mid[1]*256) + mid[2])[:2]

