import math as m
import random as r
from .base import T


class Random:
    _binom_tables = {}

    def exp_dist(self, lambda_: float) -> float:
        return -m.log(1 - r.random()) / lambda_

    def binom_dist(self, n: int, p: float) -> int:
        if (n, p) in self._binom_tables:
            table = self._binom_tables[(n, p)]
        else:
            table = self._generate_table(n, p)
            self._binom_tables[(n, p)] = table

        X = r.random()
        return next(v for v, p in table if X > p) + 1

    def _generate_table(self, n: int, p: float) -> list[tuple[int, float]]:
        table = [(-1, 0.0)] + [
            (
                k,
                m.comb(n, k)*(p**k)*(1 - p)**(n - k)
            )
            for k in range(n + 1)
        ]
        s = 0
        for i, (k, v) in enumerate(table):
            s += v
            table[i] = (k, s)

        return table[::-1]


    def choice(self, pairs: list[tuple[float, T]]) -> T:
        w = sum(w for w, _ in pairs)
        p = int(r.random()*w)
        for p1, item in pairs:
            if p >= p1:
                p -= p1
                continue
            return item
        raise