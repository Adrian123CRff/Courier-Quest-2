# python c:\ProyectoEstrucutrasDeDatos-2\Courier-Quest-2\general\ia\cpu_hard.py
from __future__ import annotations
import heapq
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple
from .cpu_easy import JobsAPI, WorldAPI
from ..game.player_stats import PlayerStats

Vec2I = Tuple[int, int]

@dataclass
class CpuConfigHard:
    step_period_sec: float = 0.14
    retarget_timeout_sec: float = 5.0
    random_repick_prob: float = 0.20
    max_carry: int = 2
    capacity_kg: float = 15.0
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0

@dataclass
class CpuInventory:
    capacity_kg: float
    items: List[str] = field(default_factory=list)
    weight: float = 0.0
    def add(self, job_id: str, weight: float) -> bool:
        w = float(weight)
        if self.weight + w > float(self.capacity_kg): return False
        self.items.append(job_id); self.weight += w; return True
    def remove(self, job_id: str, weight: float = 0.0) -> None:
        try: self.items.remove(job_id)
        except Exception: pass
        if weight: self.weight = max(0.0, self.weight - float(weight))

@dataclass
class CpuState:
    grid_pos: Vec2I
    stamina: float
    reputation: float
    money: float = 0.0
    carrying: List[str] = field(default_factory=list)
    current_job_id: Optional[str] = None
    time_since_last_step: float = 0.0
    time_since_job_pick: float = 0.0
    inventory: CpuInventory = field(default_factory=lambda: CpuInventory(15.0))

class HardCPUCourier:
    def __init__(
        self,
        is_walkable: Callable[[int, int], bool],
        jobs_api: JobsAPI,
        world_api: WorldAPI,
        target_provider: Optional[Callable[[], Vec2I]] = None,
        rng: Optional[random.Random] = None,
        config: Optional[CpuConfigHard] = None,
        initial_grid_pos: Vec2I = (0, 0),
        initial_stamina: float = 100.0,
        initial_reputation: float = 0.0,
    ) -> None:
        self.is_walkable = is_walkable
        self.jobs = jobs_api
        self.world = world_api
        self.target_provider = target_provider
        self.rng = rng or random.Random()
        self.cfg = config or CpuConfigHard()
        self.s = CpuState(
            grid_pos=initial_grid_pos,
            stamina=initial_stamina,
            reputation=initial_reputation,
            inventory=CpuInventory(self.cfg.capacity_kg),
        )
        self.stats = PlayerStats()
        self.stats.stamina = float(initial_stamina)
        try: self.stats.reputation = int(initial_reputation)
        except Exception: self.stats.reputation = 70
        self._path: List[Vec2I] = []
        self._path_target: Optional[Vec2I] = None
        self._prev_pos: Optional[Vec2I] = None

    @property
    def grid_pos(self) -> Vec2I: return self.s.grid_pos
    @property
    def stamina(self) -> float: return float(getattr(self.stats, "stamina", self.s.stamina))

    def update(self, dt: float) -> None:
        self.s.time_since_last_step += float(dt)
        self.s.time_since_job_pick += float(dt)
        if self.s.time_since_last_step < self.cfg.step_period_sec: return
        self._maybe_choose_target_job()
        self._ensure_path_to_target()
        moved = self._step_along_path()
        self.s.time_since_last_step = 0.0
        try: carry_w = float(getattr(self.s.inventory, 'weight', 0.0) or 0.0)
        except Exception: carry_w = 0.0
        try:
            st = self.world.get_weather_state()
            cond = st.get('condition', 'clear'); intensity = float(st.get('intensity', 1.0))
        except Exception:
            cond, intensity = 'clear', 1.0
        pen = self._climate_penalty_value(cond, intensity)
        try:
            self.stats.update(dt, is_moving=bool(moved), input_active=False)
            self.stats.consume_stamina(base_cost=0.5, weight=carry_w, weather_penalty=pen, intensity=intensity)
        except Exception: pass
        self.s.stamina = self.stats.stamina
        self._opportunistic_actions()

    def _maybe_choose_target_job(self) -> None:
        repick = False
        if self.s.current_job_id is None: repick = True
        elif self.s.time_since_job_pick >= self.cfg.retarget_timeout_sec: repick = True
        elif self.rng.random() < self.cfg.random_repick_prob: repick = True
        if not repick: return
        self.s.current_job_id = self._choose_best_job()
        self.s.time_since_job_pick = 0.0
        self._path = []
        self._path_target = None

    def _choose_best_job(self) -> Optional[str]:
        cur = self.s.grid_pos
        ids: List[str] = []
        try:
            if hasattr(self.jobs, 'list_active_jobs'):
                ids = self.jobs.list_active_jobs()
        except Exception:
            ids = []
        if not ids:
            try:
                ids = self.jobs.list_available_jobs()
            except Exception:
                ids = []
        if not ids:
            try: return self.jobs.pick_random_available(self.rng)
            except Exception: return None
        prelim: List[Tuple[float, str]] = []
        for jid in ids:
            try:
                info = self.jobs.get_job_info(jid)
                if not info: continue
                p = getattr(info, 'pickup', getattr(info, 'pickup_pos', None))
                d = getattr(info, 'dropoff', getattr(info, 'dropoff_pos', None))
                if not p or not d: continue
                px, py = p
                dx, dy = d
                if self.jobs.is_picked_up(jid): continue
                try:
                    w = float(getattr(info, 'weight', self.jobs.weight_of(jid)))
                except Exception:
                    w = 0.0
                if w > float(self.cfg.capacity_kg):
                    continue
                d1 = self.world.manhattan_distance(cur, (px, py))
                d2 = self.world.manhattan_distance((px, py), (dx, dy))
                prelim.append((float(d1 + d2), jid))
            except Exception:
                continue
        prelim.sort(key=lambda x: x[0])
        candidates = [jid for _, jid in prelim[:5]] or ids
        best_id, best_score = None, float("-inf")
        for jid in candidates:
            try:
                info = self.jobs.get_job_info(jid)
                if not info: continue
                p = getattr(info, 'pickup', getattr(info, 'pickup_pos', None))
                d = getattr(info, 'dropoff', getattr(info, 'dropoff_pos', None))
                if not p or not d: continue
                px, py = p
                dx, dy = d
                try:
                    w = float(getattr(info, 'weight', self.jobs.weight_of(jid)))
                except Exception:
                    w = 0.0
                if w > float(self.cfg.capacity_kg):
                    continue
                payout = float(getattr(info, 'payout', 0.0) or 0.0)
                c1 = self._dijkstra_cost(cur, (px, py))
                c2 = self._dijkstra_cost((px, py), (dx, dy))
                try: wsp = self.world.get_weather_penalty(cur)
                except Exception: wsp = 0.0
                score = (self.cfg.alpha * payout) - (self.cfg.beta * float(c1 + c2)) - (self.cfg.gamma * wsp)
                if score > best_score: best_score, best_id = score, jid
            except Exception:
                continue
        return best_id

    def _target_cell(self) -> Optional[Vec2I]:
        jid = self.s.current_job_id
        if not jid: return None
        try:
            if jid in self.s.carrying: return self.jobs.dropoff_coords(jid)
            else: return self.jobs.pickup_coords(jid)
        except Exception: return None

    def _neighbors(self, pos: Vec2I) -> List[Vec2I]:
        x, y = int(pos[0]), int(pos[1])
        cand = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        out: List[Vec2I] = []
        for nx, ny in cand:
            try:
                if self.is_walkable(int(nx), int(ny)): out.append((int(nx), int(ny)))
            except Exception: pass
        return out

    def _is_adjacent(self, a: Vec2I, b: Vec2I) -> bool:
        try:
            return int(abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))) == 1
        except Exception:
            return False

    def _heuristic(self, a: Vec2I, b: Vec2I) -> float:
        try: return float(self.world.manhattan_distance(a, b))
        except Exception: return float(abs(int(a[0])-int(b[0])) + abs(int(a[1])-int(b[1])))

    def _dijkstra(self, start: Vec2I, goal: Vec2I) -> List[Vec2I]:
        if start == goal: return []
        open_heap: List[Tuple[float, Vec2I]] = []
        heapq.heappush(open_heap, (0.0, start))
        came: dict[Vec2I, Optional[Vec2I]] = {start: None}
        g: dict[Vec2I, float] = {start: 0.0}
        while open_heap:
            cost, current = heapq.heappop(open_heap)
            if current == goal:
                path: List[Vec2I] = []
                node = current
                while node is not None:
                    path.append(node)
                    node = came.get(node)
                path.reverse()
                return path[1:]
            for n in self._neighbors(current):
                tentative = g[current] + 1.0
                if tentative < g.get(n, float("inf")):
                    came[n] = current
                    g[n] = tentative
                    heapq.heappush(open_heap, (tentative, n))
        return []

    def _dijkstra_cost(self, start: Vec2I, goal: Vec2I) -> float:
        path = self._dijkstra(start, goal)
        return float(len(path))

    def _nearest_walkable_to(self, goal: Vec2I) -> Vec2I:
        try:
            if self.is_walkable(int(goal[0]), int(goal[1])): return goal
        except Exception:
            pass
        ns = self._neighbors(goal)
        if ns:
            cur = self.s.grid_pos
            try: return min(ns, key=lambda n: self.world.manhattan_distance(n, cur))
            except Exception: return ns[0]
        return goal

    def _ensure_path_to_target(self) -> None:
        tgt = self._target_cell()
        if not tgt:
            self._path = []
            self._path_target = None
            return
        tgt = self._nearest_walkable_to(tgt)
        if self._path_target != tgt or not self._path:
            self._path = self._dijkstra(self.s.grid_pos, tgt)
            self._path_target = tgt
            if not self._path and self.s.grid_pos != tgt:
                cur = self.s.grid_pos
                neighbors = self._neighbors(cur)
                if neighbors:
                    try:
                        cand = [n for n in neighbors if n != self._prev_pos]
                        if not cand: cand = neighbors
                        best = min(cand, key=lambda n: self.world.manhattan_distance(n, tgt))
                    except Exception:
                        best = neighbors[0]
                    self._path = [best]
                else:
                    self._path = []

    def _step_along_path(self) -> bool:
        if not self._path:
            return False
        nxt = self._path[0]
        try:
            if not self.is_walkable(int(nxt[0]), int(nxt[1])):
                self._ensure_path_to_target()
                if not self._path: return False
                nxt = self._path[0]
        except Exception: pass
        prev = self.s.grid_pos
        self.s.grid_pos = nxt
        self._prev_pos = prev
        try:
            self._path = self._path[1:]
        except Exception: self._path = []
        return True

    def _opportunistic_actions(self) -> None:
        pos = self.s.grid_pos
        try: pk = self.jobs.get_pickups_at(pos)
        except Exception: pk = []
        if pk:
            for stub in pk:
                jid = getattr(stub, "id", None)
                if not jid: continue
                if len(self.s.carrying) >= int(self.cfg.max_carry): break
                try: w = float(self.jobs.weight_of(jid))
                except Exception: w = 0.0
                if w > float(self.cfg.capacity_kg): continue
                if not self.s.inventory.add(jid, w): continue
                if self.jobs.pickup(jid):
                    if jid == self.s.current_job_id: self.s.carrying.append(jid)
        else:
            jid_cur = self.s.current_job_id
            if jid_cur and (jid_cur not in self.s.carrying):
                try:
                    p = self.jobs.pickup_coords(jid_cur)
                except Exception:
                    p = None
                if p:
                    walk_ok = True
                    try: walk_ok = bool(self.is_walkable(int(p[0]), int(p[1])))
                    except Exception: walk_ok = True
                    if (not walk_ok) and self._is_adjacent(self.s.grid_pos, (int(p[0]), int(p[1]))):
                        try: w = float(self.jobs.weight_of(jid_cur))
                        except Exception: w = 0.0
                        if w <= float(self.cfg.capacity_kg):
                            if self.jobs.pickup(jid_cur):
                                self.s.carrying.append(jid_cur)
        jid = self.s.current_job_id
        if jid and jid in self.s.carrying:
            try:
                ok = self.jobs.is_dropoff_here(jid, pos)
                if not ok:
                    try:
                        d = self.jobs.dropoff_coords(jid)
                    except Exception:
                        d = None
                    if d:
                        walk_ok = True
                        try: walk_ok = bool(self.is_walkable(int(d[0]), int(d[1])))
                        except Exception: walk_ok = True
                        if (not walk_ok) and self._is_adjacent(pos, (int(d[0]), int(d[1]))):
                            ok = True
                if ok:
                    pay = self.jobs.dropoff(jid)
                    try: self.s.inventory.remove(jid, float(self.jobs.weight_of(jid)))
                    except Exception: self.s.inventory.remove(jid, 0.0)
                    try: self.s.carrying.remove(jid)
                    except Exception: pass
                    try: self.s.money += float(pay or 0.0)
                    except Exception: pass
                    self.s.current_job_id = None
                    self._path = []
                    self._path_target = None
            except Exception: pass

    def _climate_penalty_value(self, condition: str, intensity: float) -> float:
        c = str(condition or "clear").lower()
        base = 0.0
        if ("rain" in c) or ("lluv" in c): base = 0.5
        elif ("storm" in c) or ("tormenta" in c): base = 0.9
        elif ("snow" in c) or ("nieve" in c): base = 0.7
        elif ("fog" in c) or ("niebla" in c): base = 0.4
        return float(base) * float(intensity or 1.0)