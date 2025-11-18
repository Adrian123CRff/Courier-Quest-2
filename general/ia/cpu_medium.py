def _choose_best_job(self) -> Optional[str]:
        cur = self.s.grid_pos
        ids = []
        try:
            if hasattr(self.jobs, 'list_active_jobs'): ids = self.jobs.list_active_jobs()
        except Exception: ids = []
        if not ids:
            try: ids = self.jobs.list_available_jobs()
            except Exception: ids = []
        if not ids:
            try: return self.jobs.pick_random_available(self.rng)
            except Exception: return None
# file: c:\ProyectoEstrucutrasDeDatos-2\Courier-Quest-2\general\ia\cpu_medium.py
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple
from .cpu_easy import JobsAPI, WorldAPI
from ..game.player_stats import PlayerStats

Vec2I = Tuple[int, int]

@dataclass
class MediumConfig:
    step_period_sec: float = 0.20
    retarget_timeout_sec: float = 6.0
    random_repick_prob: float = 0.15
    max_carry: int = 1
    capacity_kg: float = 10.0
    alpha: float = 1.0
    beta: float = 0.8
    gamma: float = 1.0

@dataclass
class CpuInventory:
    capacity_kg: float
    items: List[str] = field(default_factory=list)
    weight: float = 0.0
    def add(self, job_id: str, weight: float) -> bool:
        if self.weight + float(weight) > float(self.capacity_kg): return False
        self.items.append(job_id); self.weight += float(weight); return True
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
    inventory: CpuInventory = field(default_factory=lambda: CpuInventory(10.0))

class MediumCPUCourier:
    def __init__(
        self,
        is_walkable: Callable[[int, int], bool],
        jobs_api: JobsAPI,
        world_api: WorldAPI,
        target_provider: Optional[Callable[[], Vec2I]] = None,
        rng: Optional[random.Random] = None,
        config: Optional[MediumConfig] = None,
        initial_grid_pos: Vec2I = (0, 0),
        initial_stamina: float = 100.0,
        initial_reputation: float = 0.0,
    ) -> None:
        self.is_walkable = is_walkable
        self.jobs = jobs_api
        self.world = world_api
        self.target_provider = target_provider
        self.rng = rng or random.Random()
        self.cfg = config or MediumConfig()
        self.s = CpuState(
            grid_pos=initial_grid_pos,
            stamina=initial_stamina,
            reputation=initial_reputation,
            inventory=CpuInventory(self.cfg.capacity_kg)
        )
        self.stats = PlayerStats()
        self.stats.stamina = float(initial_stamina)
        try: self.stats.reputation = int(initial_reputation)
        except Exception: self.stats.reputation = 70

    @property
    def grid_pos(self) -> Vec2I: return self.s.grid_pos
    @property
    def stamina(self) -> float: return float(getattr(self.stats, "stamina", self.s.stamina))

    def update(self, dt: float) -> None:
        self.s.time_since_last_step += float(dt)
        self.s.time_since_job_pick += float(dt)
        if self.s.time_since_last_step < self.cfg.step_period_sec: return
        self._maybe_choose_target_job()
        did_move = self._greedy_step()
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
            self.stats.update(dt, is_moving=bool(did_move), input_active=False)
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

    def _choose_best_job(self) -> Optional[str]:
        cur = self.s.grid_pos
        try: ids = self.jobs.list_available_jobs()
        except Exception: ids = []
        if not ids:
            try: return self.jobs.pick_random_available(self.rng)
            except Exception: return None
        best_id, best_score = None, float("-inf")
        for jid in ids:
            try:
                info = self.jobs.get_job_info(jid)
                if not info: continue
                px, py = info.pickup; dx, dy = info.dropoff
                payout = float(getattr(info, 'payout', 0.0) or 0.0)
                d1 = self.world.manhattan_distance(cur, (px, py))
                d2 = self.world.manhattan_distance((px, py), (dx, dy))
                lookahead_cost = min(3, d1) + min(3, d2)
                try: wsp = self.world.get_weather_penalty(cur)
                except Exception: wsp = 0.0
                score = (self.cfg.alpha * payout) - (self.cfg.beta * lookahead_cost) - (self.cfg.gamma * wsp)
                if score > best_score: best_score, best_id = score, jid
            except Exception: continue
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

    def _greedy_step(self) -> bool:
        tgt = self._target_cell()
        cur = self.s.grid_pos
        if not tgt: return self._random_step()
        neighbors = self._neighbors(cur)
        if not neighbors: return False
        best, best_val = None, float("-inf")
        for n in neighbors:
            try:
                d = self.world.manhattan_distance(n, tgt)
                lookahead = min(3, d)
                try: wsp = self.world.get_weather_penalty(n)
                except Exception: wsp = 0.0
                val = -(self.cfg.beta * lookahead) - (self.cfg.gamma * wsp) + self.rng.uniform(-0.02, 0.02)
                if val > best_val: best_val, best = val, n
            except Exception: continue
        if not best: return False
        self.s.grid_pos = best
        return True

    def _random_step(self) -> bool:
        cur = self.s.grid_pos
        neighbors = self._neighbors(cur)
        if not neighbors: return False
        self.s.grid_pos = self.rng.choice(neighbors)
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
                if not self.s.inventory.add(jid, w): continue
                if self.jobs.pickup(jid):
                    if jid == self.s.current_job_id: self.s.carrying.append(jid)
        jid = self.s.current_job_id
        if jid and jid in self.s.carrying:
            try:
                if self.jobs.is_dropoff_here(jid, pos):
                    pay = self.jobs.dropoff(jid)
                    try: self.s.inventory.remove(jid, float(self.jobs.weight_of(jid)))
                    except Exception: self.s.inventory.remove(jid, 0.0)
                    try: self.s.carrying.remove(jid)
                    except Exception: pass
                    try: self.s.money += float(pay or 0.0)
                    except Exception: pass
                    self.s.current_job_id = None
            except Exception: pass

    def _climate_penalty_value(self, condition: str, intensity: float) -> float:
        c = str(condition or "clear").lower()
        base = 0.0
        if ("rain" in c) or ("lluv" in c): base = 0.5
        elif ("storm" in c) or ("tormenta" in c): base = 0.9
        elif ("snow" in c) or ("nieve" in c): base = 0.7
        elif ("fog" in c) or ("niebla" in c): base = 0.4
        return float(base) * float(intensity or 1.0)