#update_manager.py
"""
Update Manager - Handles game update logic and timers
"""

import time


class UpdateManager:
    """Manages game update cycles, timers, and periodic updates."""

    def __init__(self, parent_view):
        self.parent = parent_view

    def on_update(self, dt: float) -> None:
        """Main update method that handles all game logic updates."""
        if self.parent.game_manager:
            try:
                self.parent.game_manager.update(dt)
            except Exception as e:
                print(f"Error en game_manager.update: {e}")

        # notifications timers and spawning
        self.parent.notifications.update_timers(dt)

        if self.parent.active_notification and self.parent.notification_timer > 0:
            self.parent.notification_timer -= dt
            if self.parent.notification_timer <= 0:
                self.parent.active_notification = None

        input_active = (time.time() - self.parent._last_input_time) < self.parent.INPUT_ACTIVE_WINDOW
        self.parent._ensure_inventory()
        inventory = self.parent.state.get("inventory", None) if isinstance(self.parent.state, dict) else getattr(self.parent.state, "inventory", None)
        was_moving = bool(self.parent.player.moving)

        try:
            self.parent.player.update(dt, player_stats=self.parent.player_stats, weather_system=self.parent.weather_markov, inventory=inventory)
        except Exception:
            try:
                self.parent.player.update(dt)
            except Exception:
                pass

        # ensure CPU agent exists even if initialization failed earlier
        if not getattr(self.parent, 'cpu_agent', None):
            try:
                from ..ia.cpu_easy import EasyCPUCourier, CpuConfig
                try:
                    from ..ia.cpu_medium import MediumCPUCourier, MediumConfig
                except Exception:
                    MediumCPUCourier, MediumConfig = None, None
                try:
                    from ..ia.cpu_hard import HardCPUCourier, CpuConfigHard
                except Exception:
                    HardCPUCourier, CpuConfigHard = None, None
                try:
                    from ..ia.easy_adapters import EasyJobsAdapter, EasyWorldAdapter
                except Exception:
                    class EasyJobsAdapter:
                        def __init__(self, view): self.view = view
                        def pick_random_available(self, rng):
                            jm = getattr(self.view, 'job_manager', None); gm = getattr(self.view, 'game_manager', None)
                            if not jm: return None
                            try: now = gm.get_game_time() if gm and hasattr(gm, 'get_game_time') else 0.0
                            except Exception: now = 0.0
                            av = jm.get_available_jobs(now); av = [j for j in av if not getattr(j, 'rejected', False) and not getattr(j, 'completed', False)]
                            if not av: return None
                            j = rng.choice(av); return getattr(j, 'id', None)
                        def get_pickups_at(self, cell):
                            jm = getattr(self.view, 'job_manager', None)
                            if not jm: return []
                            x, y = int(cell[0]), int(cell[1]); out = []
                            class _Wrap:
                                def __init__(self, jid): self.id = jid
                            for j in jm.all_jobs():
                                if getattr(j, 'completed', False) or getattr(j, 'rejected', False): continue
                                try: px, py = j.pickup
                                except Exception: px, py = None, None
                                if px == x and py == y:
                                    jid = getattr(j, 'id', None)
                                    if jid: out.append(_Wrap(jid))
                            return out
                        def is_dropoff_here(self, job_id, cell):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return False
                            try: dx, dy = j.dropoff
                            except Exception: dx, dy = None, None
                            return dx == int(cell[0]) and dy == int(cell[1])
                        def pickup(self, job_id):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return False
                            try:
                                # si ya está recogido por otro, no permitir
                                if getattr(j, 'picked_up', False) and getattr(j, 'carrier', None) not in (None, 'cpu'):
                                    return False
                                if not getattr(j, 'accepted', False): jm.accept_job(job_id)
                                j.picked_up = True; j.dropoff_visible = True
                                try: setattr(j, 'carrier', 'cpu')
                                except Exception: pass
                                return True
                            except Exception: return False
                        def dropoff(self, job_id):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return None
                            try:
                                if not getattr(j, 'picked_up', False): return None
                                # sólo el CPU puede entregar si él es el portador
                                if getattr(j, 'carrier', None) not in ('cpu', None):
                                    return None
                                try: base = float(getattr(j, 'raw', {}).get('payout', getattr(j, 'payout', 0.0) or 0.0))
                                except Exception: base = 0.0
                                j.completed = True
                                try:
                                    setattr(j, 'cpu_completed', True)
                                    setattr(j, 'completed_by', 'cpu')
                                    setattr(j, 'carrier', 'cpu')
                                except Exception:
                                    pass
                                return base
                            except Exception: return None
                        def weight_of(self, job_id):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return 0.0
                            try:
                                raw = getattr(j, 'raw', {}) or {}
                                w = raw.get('weight', None)
                                if w is None:
                                    w = getattr(j, 'weight', 0.0)
                                return float(w or 0.0)
                            except Exception: return 0.0
                        def get_job_info(self, job_id):
                            jm = getattr(self.view, 'job_manager', None)
                            j = jm.get_job(job_id) if jm else None
                            if not j: return None
                            try:
                                class _JobInfo:
                                    def __init__(self, jid, pickup_pos, dropoff_pos, payout, weight):
                                        self.id = jid
                                        self.pickup_pos = pickup_pos
                                        self.dropoff_pos = dropoff_pos
                                        self.payout = payout
                                        self.weight = weight
                                jid = getattr(j, 'id', None)
                                px, py = getattr(j, 'pickup', (None, None))
                                dx, dy = getattr(j, 'dropoff', (None, None))
                                payout = float(getattr(j, 'raw', {}).get('payout', getattr(j, 'payout', 0.0) or 0.0))
                                weight = float(getattr(j, 'raw', {}).get('weight', getattr(j, 'weight', 0.0) or 0.0))
                                if jid is None or px is None or py is None or dx is None or dy is None:
                                    return None
                                return _JobInfo(jid, (int(px), int(py)), (int(dx), int(dy)), payout, weight)
                            except Exception:
                                return None
                        def list_available_jobs(self):
                            jm = getattr(self.view, 'job_manager', None); gm = getattr(self.view, 'game_manager', None)
                            if not jm: return []
                            try: now = gm.get_game_time() if gm and hasattr(gm, 'get_game_time') else 0.0
                            except Exception: now = 0.0
                            out = []
                            try:
                                for j in jm.get_available_jobs(now):
                                    if getattr(j, 'rejected', False) or getattr(j, 'completed', False):
                                        continue
                                    jid = getattr(j, 'id', None)
                                    if jid: out.append(jid)
                            except Exception:
                                pass
                            return out
                        def pickup_coords(self, job_id):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return None
                            try: return getattr(j, 'pickup', None)
                            except Exception: return None
                        def dropoff_coords(self, job_id):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return None
                            try: return getattr(j, 'dropoff', None)
                            except Exception: return None
                        def is_picked_up(self, job_id):
                            jm = getattr(self.view, 'job_manager', None); j = jm.get_job(job_id) if jm else None
                            if not j: return False
                            try: return bool(getattr(j, 'picked_up', False))
                            except Exception: return False
                    class EasyWorldAdapter:
                        def __init__(self, view=None): self.view = view
                        def base_move_cost(self): return 1.0
                        def reputation_gain_on_delivery(self): return 1.0
                        def current_weather(self):
                            try:
                                if self.view and hasattr(self.view, 'weather'):
                                    return str(self.view.weather.get_current_condition_name())
                            except Exception:
                                pass
                            return 'clear'
                        def get_weather_state(self):
                            try:
                                if self.view and hasattr(self.view, 'weather') and hasattr(self.view.weather, 'get_state'):
                                    return dict(self.view.weather.get_state())
                            except Exception:
                                pass
                            return {'condition': self.current_weather(), 'intensity': 1.0}
                        def get_weather_penalty(self, pos):
                            try:
                                if self.view and hasattr(self.view, 'weather'):
                                    st = {}
                                    try:
                                        if hasattr(self.view.weather, 'get_state'):
                                            st = dict(self.view.weather.get_state())
                                    except Exception:
                                        st = {}
                                    try:
                                        cond = str(self.view.weather.get_current_condition_name())
                                    except Exception:
                                        cond = ''
                                    intensity = float(st.get('intensity', 1.0) or 1.0)
                                    base = 0.0
                                    k = cond.lower()
                                    if ('rain' in k) or ('lluv' in k):
                                        base = 0.5
                                    elif ('storm' in k) or ('tormenta' in k):
                                        base = 0.9
                                    elif ('snow' in k) or ('nieve' in k):
                                        base = 0.7
                                    return float(base) * float(intensity)
                            except Exception:
                                pass
                            return 0.0
                        def manhattan_distance(self, pos1, pos2):
                            try:
                                x1, y1 = int(pos1[0]), int(pos1[1])
                                x2, y2 = int(pos2[0]), int(pos2[1])
                                return abs(x1 - x2) + abs(y1 - y2)
                            except Exception:
                                return 0
                        def is_walkable(self, pos):
                            try:
                                if self.view and hasattr(self.view, 'game_map'):
                                    return bool(self.view.game_map.is_walkable(int(pos[0]), int(pos[1])))
                            except Exception:
                                pass
                            return True
                sx, sy = int(self.parent.player.cell_x), int(self.parent.player.cell_y)
                diff = str(getattr(self.parent, 'cpu_difficulty', 'easy') or 'easy').lower()
                if diff == 'medium':
                    cfg = MediumConfig() if MediumConfig else CpuConfig(step_period_sec=0.20, retarget_timeout_sec=6.0, random_repick_prob=0.15, max_carry=1)
                elif diff == 'hard':
                    cfg = CpuConfigHard() if CpuConfigHard else CpuConfig(step_period_sec=0.14, retarget_timeout_sec=5.0, random_repick_prob=0.20, max_carry=2)
                else:
                    cfg = CpuConfig(step_period_sec=0.30, retarget_timeout_sec=8.0, random_repick_prob=0.10, max_carry=1)
                if diff == 'medium' and MediumCPUCourier:
                    self.parent.cpu_agent = MediumCPUCourier(
                        self.parent.game_map.is_walkable,
                        EasyJobsAdapter(self.parent),
                        EasyWorldAdapter(self.parent),
                        initial_grid_pos=(sx, sy),
                        initial_reputation=int(getattr(self.parent.player_stats, 'reputation', 70)),
                        config=cfg
                    )
                    try:
                        print("[CPU] Instanciado MediumCPUCourier")
                    except Exception:
                        pass
                elif diff == 'hard' and HardCPUCourier:
                    self.parent.cpu_agent = HardCPUCourier(
                        self.parent.game_map.is_walkable,
                        EasyJobsAdapter(self.parent),
                        EasyWorldAdapter(self.parent),
                        initial_grid_pos=(sx, sy),
                        initial_reputation=int(getattr(self.parent.player_stats, 'reputation', 70)),
                        config=cfg
                    )
                    try:
                        print("[CPU] Instanciado HardCPUCourier")
                    except Exception:
                        pass
                else:
                    self.parent.cpu_agent = EasyCPUCourier(
                        self.parent.game_map.is_walkable,
                        EasyJobsAdapter(self.parent),
                        EasyWorldAdapter(self.parent),
                        initial_grid_pos=(sx, sy),
                        initial_reputation=int(getattr(self.parent.player_stats, 'reputation', 70)),
                        config=cfg
                    )
                    try:
                        print("[CPU] Instanciado EasyCPUCourier")
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            if getattr(self.parent, 'cpu_agent', None):
                self.parent.cpu_agent.update(dt)
        except Exception:
            pass

        if was_moving and not self.parent.player.moving:
            try:
                if self.parent.game_manager and hasattr(self.parent.game_manager, 'on_player_step_completed'):
                    self.parent.game_manager.on_player_step_completed()
            except Exception:
                pass
            px = int(self.parent.player.cell_x)
            py = int(self.parent.player.cell_y)

            picked_up = False
            if self.parent.game_manager and hasattr(self.parent.game_manager, 'try_pickup_at'):
                try:
                    picked_up = self.parent.game_manager.try_pickup_at(px, py)
                except Exception as e:
                    print(f"Error en try_pickup_at: {e}")

            if not picked_up:
                picked_up = self.parent.jobs_logic.pickup_nearby()

            if picked_up:
                self.parent.show_notification("¡Paquete recogido! Ve al punto de entrega.")

            delivered = False
            if self.parent.game_manager and hasattr(self.parent.game_manager, 'try_deliver_at'):
                try:
                    result = self.parent.game_manager.try_deliver_at(px, py)
                    if result:
                        delivered = True
                        try:
                            jid = result.get('job_id') if isinstance(result, dict) else None
                            job = self.parent.job_manager.get_job(jid) if (jid and self.parent.job_manager) else None
                        except Exception:
                            job = None

                        # **Remover del inventario también en el flujo de GameManager**
                        self.parent.jobs_logic.remove_job_from_inventory(job)

                        # asegurar estado del job
                        try:
                            if job and not getattr(job, "completed", False):
                                job.completed = True
                        except Exception:
                            pass

                        pay_hint = 0.0
                        try:
                            if isinstance(result, dict):
                                pay_hint = result.get("pay", 0)
                        except Exception:
                            pass
                        pay = self.parent._get_job_payout(job) if job is not None else self.parent._parse_money(pay_hint)

                        on_time = True
                        try:
                            if hasattr(self.parent.game_manager, "get_job_time_remaining"):
                                rem = self.parent.game_manager.get_job_time_remaining(
                                    getattr(job, "raw", {}) if job is not None else {}
                                )
                                # on_time = True si no hay deadline o si aún hay tiempo restante
                                on_time = (rem == float("inf")) or (rem >= 0)
                        except Exception:
                            pass

                        self.parent.jobs_logic.notify_delivery(job, pay, on_time)

                        if isinstance(result, dict):
                            jid = result.get('job_id', '¿?')
                            self.parent.show_notification(f"¡Pedido {jid} entregado!\n+${pay:.0f}")
                        else:
                            self.parent.show_notification(f"¡Pedido entregado! +${pay:.0f}")
                except Exception as e:
                    print(f"Error deliver (GameManager): {e}")

            if not delivered:
                delivered = self.parent.jobs_logic.try_deliver_at_position(px, py)
                if delivered:
                    self.parent.show_notification("¡Pedido entregado! +$")

        # 1) pagar entregas no contabilizadas
        self.parent.jobs_logic.synchronize_money_with_completed_jobs()
        # 2) y forzar consistencia si algo lo desfasó
        self.parent.jobs_logic.recompute_money_from_jobs()

        # 3) verificar condiciones de fin de partida y registrar puntaje
        try:
            prev_game_over = getattr(self.parent, "_game_over", False)
            self.parent.endgame.check_and_maybe_end()
            if getattr(self.parent, "_game_over", False) and not prev_game_over:
                money = self.parent._get_state_money()
                goal = self.parent.endgame._compute_goal()
                rep = getattr(self.parent.player_stats, "reputation", 70)
                try:
                    time_remaining = float(self.parent.game_manager.get_time_remaining()) if self.parent.game_manager else 0.0
                except Exception:
                    time_remaining = 0.0
                self.parent._show_endgame_overlay = True
                if money >= goal:
                    self.parent._endgame_title = "🏆 ¡Victoria!"
                    self.parent._endgame_reason = "Has alcanzado la meta de ingresos. ¡Felicitaciones!"
                elif rep <= 20:
                    self.parent._endgame_title = "❌ Juego Finalizado"
                    self.parent._endgame_reason = "Has alcanzado el mínimo de reputación. Inténtalo nuevamente."
                    self.parent._show_lose_overlay = True
                    self.parent._lose_reason = "Reputación baja"
                else:
                    self.parent._endgame_title = "⏰ Tiempo agotado"
                    self.parent._endgame_reason = "El tiempo se terminó. Inténtalo nuevamente."
                    self.parent._show_lose_overlay = True
                    self.parent._lose_reason = "Tiempo agotado"
        except Exception as e:
            print(f"[ENDGAME] Error: {e}")

        try:
            current_weather = self.parent.weather.get_current_condition_name()
            self.parent.player_stats.update(
                dt,
                bool(self.parent.player.moving),
                getattr(self, "at_rest_point", False),
                float(getattr(inventory, "current_weight", 0.0)) if inventory is not None else 0.0,
                current_weather,
                input_active=input_active
            )
        except Exception as e:
            print(f"Error actualizando player_stats: {e}")

        # unified weather update/render state propagation
        self.parent.weather.update_and_render(dt)
