# courier_quest/general/ia/easy_adapters.py
from __future__ import annotations

import random
from typing import List, Optional, Tuple, Any

from .cpu_easy import JobsAPI, WorldAPI


Vec2I = Tuple[int, int]


class EasyJobsAdapter(JobsAPI):
    """
    Adaptador para mapear la IA (JobsAPI) a tu infraestructura real:
    - Usa view.job_manager para listar trabajos.
    - Usa los helpers de view para leer pickup/dropoff.
    - Marca picked_up/completed dentro del mismo JobManager (CPU compite con humano).
    NOTA: No suma dinero al jugador humano; sólo “roba” la entrega.
    """

    def __init__(self, view: Any) -> None:
        self.v = view
        self.jm = getattr(view, "job_manager", None)

    # -------- helpers internos --------
    def _all_jobs(self):
        if self.jm and hasattr(self.jm, "all_jobs"):
            try:
                return list(self.jm.all_jobs())
            except Exception:
                return []
        return []

    def _get_job(self, job_id: str):
        if self.jm and hasattr(self.jm, "get_job"):
            try:
                return self.jm.get_job(job_id)
            except Exception:
                return None
        return None

    def _pickup_of(self, job) -> Optional[Vec2I]:
        try:
            return self.v._get_job_pickup_coords(job)
        except Exception:
            return None

    def _dropoff_of(self, job) -> Optional[Vec2I]:
        try:
            return self.v._get_job_dropoff_coords(job)
        except Exception:
            return None

    # -------- API requerida por la IA --------
    def pick_random_available(self, rng: random.Random) -> Optional[str]:
        # “Disponibles”: trabajos no completados; si ya están picked_up por humano, igual
        # pueden existir, pero el CPU no podrá recogerlos.
        jobs = [j for j in self._all_jobs() if not getattr(j, "completed", False)]
        if not jobs:
            return None
        choice = rng.choice(jobs)
        return getattr(choice, "id", None)

    def get_pickups_at(self, cell: Vec2I) -> List["JobsAPI._Job"]:
        out: List[JobsAPI._Job] = []
        cx, cy = int(cell[0]), int(cell[1])
        for j in self._all_jobs():
            if getattr(j, "completed", False):
                continue
            if getattr(j, "picked_up", False):
                continue
            p = self._pickup_of(j)
            if p and int(p[0]) == cx and int(p[1]) == cy:
                jid = getattr(j, "id", None)
                if jid:
                    out.append(JobsAPI._Job(jid))
        return out

    def is_dropoff_here(self, job_id: str, cell: Vec2I) -> bool:
        j = self._get_job(job_id)
        if not j:
            return False
        d = self._dropoff_of(j)
        if not d:
            return False
        return int(d[0]) == int(cell[0]) and int(d[1]) == int(cell[1])

    def pickup_coords(self, job_id: str) -> Optional[Vec2I]:
        j = self._get_job(job_id)
        if not j:
            return None
        return self._pickup_of(j)

    def dropoff_coords(self, job_id: str) -> Optional[Vec2I]:
        j = self._get_job(job_id)
        if not j:
            return None
        return self._dropoff_of(j)

    def weight_of(self, job_id: str) -> float:
        j = self._get_job(job_id)
        if not j:
            return 0.0
        try:
            raw = getattr(j, 'raw', {}) or {}
            w = raw.get('weight', None)
            if w is None:
                w = getattr(j, 'weight', 0.0)
            return float(w or 0.0)
        except Exception:
            return 0.0

    def get_job_info(self, job_id: str) -> Optional[JobsAPI._Job]:
        j = self._get_job(job_id)
        if not j:
            return None
        try:
            px = self._pickup_of(j)
            dx = self._dropoff_of(j)
            if not px or not dx:
                return None
            payout = float(getattr(j, 'raw', {}).get('payout', getattr(j, 'payout', 0.0) or 0.0))
            weight = float(getattr(j, 'raw', {}).get('weight', getattr(j, 'weight', 0.0) or 0.0))
            jid = getattr(j, 'id', None)
            if not jid:
                return None
            # Reusar contenedor JobsAPI._Job compatible con Medium/Hard
            obj = JobsAPI._Job(jid, (int(px[0]), int(px[1])), (int(dx[0]), int(dx[1])), payout, weight)
            return obj
        except Exception:
            return None

    def list_available_jobs(self) -> List[str]:
        out: List[str] = []
        try:
            for j in self._all_jobs():
                if getattr(j, 'completed', False) or getattr(j, 'rejected', False):
                    continue
                jid = getattr(j, 'id', None)
                if jid:
                    out.append(jid)
        except Exception:
            pass
        return out

    def is_picked_up(self, job_id: str) -> bool:
        j = self._get_job(job_id)
        if not j:
            return False
        try:
            return bool(getattr(j, 'picked_up', False))
        except Exception:
            return False

    def pickup(self, job_id: str) -> bool:
        j = self._get_job(job_id)
        if not j:
            return False
        if getattr(j, "completed", False) or getattr(j, "picked_up", False):
            # si está recogido por otro agente, no permitir
            if getattr(j, "carrier", None) not in (None, "cpu"):
                return False
            return False
        try:
            j.picked_up = True
            try:
                setattr(j, "carrier", "cpu")
            except Exception:
                pass
            return True
        except Exception:
            return False

    def dropoff(self, job_id: str) -> Optional[float]:
        j = self._get_job(job_id)
        if not j:
            return None
        if getattr(j, "completed", False) or not getattr(j, "picked_up", False):
            return None
        # sólo el CPU puede entregar si él es el portador
        if getattr(j, "carrier", None) not in ("cpu", None):
            return None
        # Marcar completado (CPU no suma dinero al humano).
        try:
            j.completed = True
            setattr(j, "cpu_completed", True)
            setattr(j, "completed_by", "cpu")
            setattr(j, "carrier", "cpu")
        except Exception:
            pass
        # Si quieres “bloquear” el inventario del humano por si acaso:
        try:
            inv = self.v.state.get("inventory") if isinstance(self.v.state, dict) else getattr(self.v.state, "inventory", None)
            if inv and hasattr(inv, "deque"):
                inv.deque = [item for item in inv.deque if getattr(item, "id", None) != getattr(j, "id", None)]
        except Exception:
            pass
        # Retornar payout sólo informativo (no se suma al humano)
        try:
            return float(getattr(j, "payout", 0.0) or 0.0)
        except Exception:
            return 0.0


class EasyWorldAdapter(WorldAPI):
    """Costos y ganancias constantes para el CPU Fácil."""
    def __init__(self, view: Any = None, move_cost: float = 1.0, rep_gain: float = 1.0) -> None:
        self._mc = float(move_cost)
        self._rg = float(rep_gain)
        self._view = view

    def base_move_cost(self) -> float:
        return self._mc

    def reputation_gain_on_delivery(self) -> float:
        return self._rg

    def current_weather(self) -> str:
        try:
            if self._view and hasattr(self._view, "weather"):
                w = getattr(self._view, "weather")
                if hasattr(w, "get_current_condition_name"):
                    return str(w.get_current_condition_name())
                # Fallback si sólo hay estado disponible
                if hasattr(w, "get_state"):
                    st = w.get_state()
                    if isinstance(st, dict) and "condition" in st:
                        return str(st.get("condition", "clear"))
        except Exception:
            pass
        return "clear"

    def get_weather_state(self) -> dict:
        try:
            v = self._view
            if v and hasattr(v, "weather_markov") and hasattr(v.weather_markov, "get_state"):
                st = v.weather_markov.get_state()
                if isinstance(st, dict):
                    return dict(st)
            if v and hasattr(v, "state") and isinstance(v.state, dict):
                ws = v.state.get("weather_state")
                if isinstance(ws, dict) and ws:
                    return dict(ws)
        except Exception:
            pass
        return {"condition": self.current_weather(), "intensity": 1.0, "multiplier": 1.0}

    def get_weather_penalty(self, pos: Vec2I) -> float:
        try:
            cond = self.current_weather().lower()
            intensity = 1.0
            try:
                st = self.get_weather_state()
                intensity = float(st.get('intensity', 1.0) or 1.0)
            except Exception:
                intensity = 1.0
            base = 0.0
            if ('rain' in cond) or ('lluv' in cond):
                base = 0.5
            elif ('storm' in cond) or ('tormenta' in cond):
                base = 0.9
            elif ('snow' in cond) or ('nieve' in cond):
                base = 0.7
            return float(base) * float(intensity)
        except Exception:
            return 0.0

    def manhattan_distance(self, pos1: Vec2I, pos2: Vec2I) -> int:
        try:
            x1, y1 = int(pos1[0]), int(pos1[1])
            x2, y2 = int(pos2[0]), int(pos2[1])
            return abs(x1 - x2) + abs(y1 - y2)
        except Exception:
            return 0

    def is_walkable(self, pos: Vec2I) -> bool:
        try:
            if self._view and hasattr(self._view, 'game_map'):
                return bool(self._view.game_map.is_walkable(int(pos[0]), int(pos[1])))
        except Exception:
            return True
        return True
