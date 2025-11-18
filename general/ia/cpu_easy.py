# courier_quest/general/ia/cpu_easy.py
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple, Any
from ..game.player_stats import PlayerStats

Vec2I = Tuple[int, int]


# ============================ Config & State ============================

@dataclass
class CpuConfig:
    """Parámetros de comportamiento del CPU en modo fácil."""
    step_period_sec: float = 0.30
    retarget_timeout_sec: float = 8.0
    random_repick_prob: float = 0.10
    max_carry: int = 1
    recover_per_sec: float = 0.4
    capacity_kg: float = 10.0
    use_pure_random_move: bool = False
    movement_bias_prob: float = 0.50


@dataclass
class CpuInventory:
    capacity_kg: float
    items: List[str] = field(default_factory=list)
    weight: float = 0.0
    def add(self, job_id: str, weight: float) -> bool:
        if self.weight + float(weight) > float(self.capacity_kg):
            return False
        self.items.append(job_id)
        self.weight += float(weight)
        return True
    def remove(self, job_id: str, weight: float = 0.0) -> None:
        try:
            self.items.remove(job_id)
        except Exception:
            pass
        if weight:
            self.weight = max(0.0, self.weight - float(weight))

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


# ============================ Adaptadores ============================

class JobsAPI:
    """
    Adaptador mínimo para interactuar con tu JobsManager real.
    Debes mapear estas funciones a tu implementación existente.
    """

    class _Job:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    def pick_random_available(self, rng: random.Random) -> Optional[str]:
        """Devuelve el id de un job disponible al azar o None."""
        raise NotImplementedError

    def get_pickups_at(self, cell: Vec2I) -> List["_Job"]:
        """Jobs que se pueden recoger en la celda específica."""
        raise NotImplementedError

    def is_dropoff_here(self, job_id: str, cell: Vec2I) -> bool:
        """True si el job se entrega en esta celda."""
        raise NotImplementedError

    def pickup(self, job_id: str) -> bool:
        """Intenta marcar el job como recogido por este jugador CPU."""
        raise NotImplementedError

    def dropoff(self, job_id: str) -> Optional[float]:
        """Intenta entregar el job. Devuelve payout si tuvo éxito."""
        raise NotImplementedError

    def weight_of(self, job_id: str) -> float:
        """Peso del pedido (0 si desconocido)."""
        raise NotImplementedError

    def pickup_coords(self, job_id: str) -> Optional[Vec2I]:
        """Coordenadas de recogida del pedido."""
        raise NotImplementedError

    def dropoff_coords(self, job_id: str) -> Optional[Vec2I]:
        """Coordenadas de entrega del pedido."""
        raise NotImplementedError

    def is_picked_up(self, job_id: str) -> bool:
        """True si el pedido ya fue recogido por alguien más."""
        raise NotImplementedError


class WorldAPI:
    """
    Adaptador mínimo para costos/beneficios del mundo (clima, reputación, etc.).
    En modo fácil, usamos costos fijos sencillos.
    """

    def base_move_cost(self) -> float:
        return 1.0

    def reputation_gain_on_delivery(self) -> float:
        return 1.0

    def current_weather(self) -> str:
        return "clear"

    def move_cost_multiplier(self, weather: str, carry_weight: float) -> float:
        w_mult = {
            "clear": 1.0, "clouds": 1.0, "rain": 1.2, "storm": 1.4,
            "wind": 1.1, "heat": 1.2, "cold": 1.1, "fog": 1.05
        }.get(str(weather), 1.0)
        weight_mult = 1.0 + 0.08 * max(0.0, float(carry_weight))
        return w_mult * weight_mult


# ============================ CPU Fácil ============================

class EasyCPUCourier:
    """
    IA nivel fácil para Courier Quest:
    - Elige un pedido disponible al azar.
    - Se mueve aleatoriamente por calles (evita celdas no caminables).
    - Entrega si por casualidad pasa por pickup/dropoff.
    - Ocasionalmente “se arrepiente” y rerollea pedido.
    """

    def __init__(
        self,
        is_walkable: Callable[[int, int], bool],
        jobs_api: JobsAPI,
        world_api: WorldAPI,
        target_provider: Optional[Callable[[], Vec2I]] = None,
        rng: Optional[random.Random] = None,
        config: Optional[CpuConfig] = None,
        initial_grid_pos: Vec2I = (0, 0),
        initial_stamina: float = 100.0,
        initial_reputation: float = 0.0,
    ) -> None:
        """
        Args:
            is_walkable: función (x, y) -> bool que indica si una celda es transitable.
            jobs_api: adaptador para interactuar con los pedidos.
            world_api: adaptador para interactuar con el mundo (pickup/drop, costos, etc.).
            rng: generador aleatorio (inyectable para tests).
            config: configuración del comportamiento.
            initial_grid_pos: posición inicial en grilla.
        """
        self.is_walkable = is_walkable
        self.jobs = jobs_api
        self.world = world_api
        self.target_provider = target_provider
        self.rng = rng or random.Random()
        self.cfg = config or CpuConfig()
        self.s = CpuState(
            grid_pos=initial_grid_pos,
            stamina=initial_stamina,
            reputation=initial_reputation,
            inventory=CpuInventory(self.cfg.capacity_kg)
        )
        self.stats = PlayerStats()
        self.stats.stamina = float(initial_stamina)
        try:
            self.stats.reputation = int(initial_reputation)
        except Exception:
            self.stats.reputation = 70

    # ——————————————— API pública ———————————————

    @property
    def grid_pos(self) -> Vec2I:
        return self.s.grid_pos

    @property
    def stamina(self) -> float:
        return float(getattr(self.stats, "stamina", self.s.stamina))

    @property
    def reputation(self) -> float:
        return float(getattr(self.stats, "reputation", self.s.reputation))

    def update(self, dt: float) -> None:
        """
        Se llama cada frame/tick. Maneja:
        - (re)selección de pedido
        - movimiento aleatorio
        - pickup / dropoff oportunista
        """
        # Timers
        self.s.time_since_last_step += dt
        self.s.time_since_job_pick += dt

        # 1) Asegurar que tenga un objetivo (pedido actual)
        self._ensure_job_target()

        did_move = False
        # Fórmula de velocidad equivalente al jugador
        climate_mul = 1.0
        try:
            st = self.world.get_weather_state()
            climate_mul = float(st.get('multiplier', 1.0))
        except Exception:
            climate_mul = 1.0
        try:
            carry_w = float(getattr(self.s.inventory, 'weight', 0.0) or 0.0)
        except Exception:
            carry_w = 0.0
        weight_mul = max(0.8, 1.0 - 0.03 * max(0.0, carry_w))
        rep_mul = 1.03 if float(getattr(self.stats, 'reputation', 70)) >= 90 else 1.0
        stamina_mul = 1.0
        try:
            stamina_mul = float(self.stats.get_speed_multiplier())
        except Exception:
            stamina_mul = 1.0
        BASE_CELLS_PER_SEC = 3.0
        cells_per_sec = BASE_CELLS_PER_SEC * climate_mul * weight_mul * rep_mul * stamina_mul
        effective_period = 1.0 / max(0.05, cells_per_sec)
        effective_period = max(0.18, min(0.50, effective_period))
        if self.s.time_since_last_step >= effective_period:
            did_move = self._random_step()
            self.s.time_since_last_step = 0.0

        try:
            self.stats.update(dt, is_moving=bool(did_move), input_active=False)
            self.s.stamina = self.stats.stamina
        except Exception:
            pass

        self._opportunistic_actions()

    # ——————————————— Lógica interna ———————————————

    def _ensure_job_target(self) -> None:
        if self.s.carrying:
            return
        need_new = False
        cid = self.s.current_job_id
        if cid is None:
            need_new = True
        else:
            if self.s.time_since_job_pick >= self.cfg.retarget_timeout_sec:
                need_new = True
            elif self.rng.random() < self.cfg.random_repick_prob:
                need_new = True
            else:
                try:
                    if self.jobs.is_picked_up(cid):
                        need_new = True
                    else:
                        pc = self.jobs.pickup_coords(cid)
                        if pc is not None:
                            here_list = self.jobs.get_pickups_at(pc)
                            if not any(j.id == cid for j in here_list):
                                need_new = True
                except Exception:
                    pass
        if need_new:
            job_id = self.jobs.pick_random_available(self.rng)
            if job_id is not None:
                self.s.current_job_id = job_id
                self.s.time_since_job_pick = 0.0

    def _get_climate_penalty_value(self, weather_cond: str) -> float:
        if weather_cond in ["rain", "wind"]:
            return 0.1
        if weather_cond == "storm":
            return 0.3
        if weather_cond == "heat":
            return 0.2
        return 0.0

    def _random_step(self) -> bool:
        x, y = self.s.grid_pos
        neighbors: List[Vec2I] = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        walkable = [p for p in neighbors if self.is_walkable(p[0], p[1])]
        if not walkable:
            return False

        try:
            if hasattr(self.stats, "can_move") and not self.stats.can_move():
                return False
        except Exception:
            pass

        # objetivo del CPU: pickup del job actual o dropoff de lo que lleva
        target = None
        try:
            if self.s.carrying:
                jid = self.s.carrying[0]
                target = self.jobs.dropoff_coords(jid)
            elif self.s.current_job_id:
                target = self.jobs.pickup_coords(self.s.current_job_id)
        except Exception:
            target = None

        if target is not None:
            if getattr(self.cfg, "use_pure_random_move", False):
                next_pos = self.rng.choice(walkable)
            else:
                if self.rng.random() < float(getattr(self.cfg, "movement_bias_prob", 0.30)):
                    tx, ty = int(target[0]), int(target[1])
                    def md(p: Vec2I) -> int:
                        return abs(p[0] - tx) + abs(p[1] - ty)
                    walkable.sort(key=md)
                    best = md(walkable[0])
                    candidates = [p for p in walkable if md(p) == best]
                    next_pos = self.rng.choice(candidates)
                else:
                    next_pos = self.rng.choice(walkable)
        else:
            next_pos = self.rng.choice(walkable)

        try:
            carry_w = float(getattr(self.s.inventory, 'weight', 0.0) or 0.0)
        except Exception:
            carry_w = 0.0
        cond, intensity = "clear", 1.0
        try:
            if hasattr(self.world, "get_weather_state"):
                st = self.world.get_weather_state() or {}
                cond = st.get("condition", "clear")
                intensity = float(st.get("intensity", 1.0))
            else:
                cond = str(self.world.current_weather())
        except Exception:
            cond, intensity = "clear", 1.0
        pen = self._get_climate_penalty_value(cond)
        try:
            self.stats.consume_stamina(base_cost=0.5, weight=carry_w, weather_penalty=pen, intensity=intensity)
        except Exception:
            pass
        self.s.grid_pos = next_pos
        self.s.stamina = self.stats.stamina
        return True

    def _opportunistic_actions(self) -> None:
        """
        Si está sobre una celda de pickup/drop que le sirve, ejecuta acción.
        Mantiene la simplicidad: un slot de carga.
        """
        cell = self.s.grid_pos

        # 1) PICKUP con tolerancia de adyacencia
        if not self.s.carrying:
            job_id = self.s.current_job_id
            pickup_here = self.jobs.get_pickups_at(cell)
            candidate = None
            if job_id and any(j.id == job_id for j in pickup_here):
                candidate = job_id
            elif pickup_here:
                candidate = pickup_here[0].id
            else:
                # adyacencia (Manhattan <= 1) para el objetivo actual
                try:
                    if job_id:
                        pc = self.jobs.pickup_coords(job_id)
                        if pc is not None:
                            if abs(pc[0] - cell[0]) + abs(pc[1] - cell[1]) <= 1:
                                candidate = job_id
                except Exception:
                    pass
            if candidate and len(self.s.carrying) < self.cfg.max_carry:
                ok = False
                try:
                    ok = self.jobs.pickup(candidate)
                except Exception:
                    ok = False
                if ok:
                    w = 0.0
                    try:
                        w = float(self.jobs.weight_of(candidate) or 0.0)
                    except Exception:
                        w = 0.0
                    if self.s.inventory.add(candidate, w):
                        self.s.carrying.append(candidate)

        # 2) DROPOFF con tolerancia de adyacencia
        if self.s.carrying:
            to_drop = list(self.s.carrying)
            for jid in to_drop:
                is_here = False
                if self.jobs.is_dropoff_here(jid, cell):
                    is_here = True
                else:
                    try:
                        dc = self.jobs.dropoff_coords(jid)
                        if dc is not None and abs(dc[0] - cell[0]) + abs(dc[1] - cell[1]) <= 1:
                            is_here = True
                    except Exception:
                        pass
                if is_here:
                    payout = self.jobs.dropoff(jid)
                    if payout is not None:
                        self.s.carrying.remove(jid)
                        try:
                            w = float(self.jobs.weight_of(jid) or 0.0)
                        except Exception:
                            w = 0.0
                        self.s.inventory.remove(jid, w)
                        try:
                            self.stats.update_reputation("delivery_on_time")
                        except Exception:
                            try:
                                self.s.reputation += self.world.reputation_gain_on_delivery()
                            except Exception:
                                pass
                        try:
                            self.s.money += float(payout)
                        except Exception:
                            pass
                        if self.s.current_job_id == jid:
                            self.s.current_job_id = None

    # ——————————————— Render opcional ———————————————

    def draw_debug(self, draw_fn: Callable[[Vec2I, str], None]) -> None:
        """
        Dibuja texto debug sobre la celda actual (si tu motor lo permite).
        Args:
            draw_fn: función (grid_pos, text) -> None para renderizar debug.
        """
        text = f"CPU(F): st={self.s.stamina:.0f} rep={self.s.reputation:.0f}"
        draw_fn(self.s.grid_pos, text)
