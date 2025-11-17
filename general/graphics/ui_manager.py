"""
UI Manager - Handles all UI drawing operations
"""

import arcade
from arcade import Text
from .drawing_utils import _draw_rect_lrbt_filled, _draw_rect_lrbt_outline


class UIManager:
    """Manages all UI drawing operations and elements."""

    def __init__(self, parent_view):
        self.parent = parent_view

    def on_draw(self) -> None:
        """Main draw method that orchestrates all UI drawing."""
        self.parent.clear()
        self.parent.game_map.draw_debug(tile_size=self.parent.TILE_SIZE, draw_grid_lines=True)
        self.parent.jobs_logic.draw_job_markers()
        self.parent.player.draw()
        self._draw_panel()
        # HUD tipo tarjeta arriba-izquierda
        try:
            self._draw_hud_card()
        except Exception:
            pass
        # self.time_panel.draw()  # Removed: now in HUD card
        try:
            self.parent.weather_renderer.draw()
        except Exception:
            pass
        try:
            if hasattr(self.parent, "cpu_agent") and self.parent.cpu_agent:
                cx, cy = self.parent.cpu_agent.grid_pos
                px, py = self.parent._cell_to_pixel(int(cx), int(cy))
                r = int(self.parent.TILE_SIZE * 0.48)
                arcade.draw_circle_filled(px, py, r, (255, 64, 160))
                arcade.draw_circle_outline(px, py, r, (255, 255, 255), 3)
            else:
                px, py = self.parent._cell_to_pixel(int(self.parent.player.cell_x), int(self.parent.player.cell_y))
                r = int(self.parent.TILE_SIZE * 0.40)
                arcade.draw_circle_filled(px, py, r, (255, 220, 40))
                arcade.draw_circle_outline(px, py, r, (255, 255, 255), 2)
        except Exception:
            pass
        self.parent.notifications.draw()

        if self.parent.active_notification and self.parent.notification_timer > 0:
            self.parent.notification_text.text = self.parent.active_notification
            self.parent.notification_text.anchor_x = "left"
            self.parent.notification_text.anchor_y = "center"
            self.parent.notification_text.x = int(getattr(self.parent, "SCREEN_WIDTH", self.parent.width)) - 350
            self.parent.notification_text.y = 200
            self.parent.notification_text.draw()

        if getattr(self.parent, "_show_endgame_overlay", False) or getattr(self.parent, "_show_lose_overlay", False):
            self._draw_endgame_overlay()

    def _draw_panel(self):
        """Draw the main side panel."""
        # self.right_panel.draw_frame()  # Removed: replaced by HUD card

        # --- Inventario con navegación ---
        self._draw_inventory_panel()

        # --- Pedidos activos ---
        self.parent.active_jobs_ui.draw()

        # --- Botón de deshacer ---
        self._draw_undo_button()

    def _draw_hud_card(self):
        """Draw the HUD card with game stats."""
        # Medidas responsivas - ahora en el lado derecho
        w = getattr(self.parent, 'SCREEN_WIDTH', self.parent.width)
        h = getattr(self.parent, 'SCREEN_HEIGHT', self.parent.height)
        map_width = getattr(self.parent, 'MAP_WIDTH', 730)
        card_w = int(min(350, (w - map_width) * 0.9))
        card_h = 180  # Reducido para que quepa todo
        left = map_width + 10
        top = h - 10
        bottom = top - card_h
        right = left + card_w
        # Fondo del HUD removido

        # Función para dibujar barras de progreso más pequeñas
        def draw_progress_bar(x, y, width, height, value01, fill_color, bg_color=(40, 45, 60)):
            _draw_rect_lrbt_filled(x, x + width, y - height, y, bg_color)
            _draw_rect_lrbt_outline(x, x + width, y - height, y, (60, 70, 90), 1)
            fill_width = int(max(0, min(1, value01)) * width)
            if fill_width > 0:
                _draw_rect_lrbt_filled(x, x + fill_width, y - height, y, fill_color)

        # Tiempo - más compacto
        try:
            gm = self.parent.game_manager
            rem = gm.get_time_remaining() if gm else 0
            m = int(rem // 60); s = int(rem % 60)
            Text("⏰ Tiempo", left + 12, top - 20, (200, 210, 220), 10).draw()
            Text(f"{m:02d}:{s:02d}", left + 12, top - 32, (240, 246, 255), 12, bold=True).draw()
        except Exception:
            Text("⏰ Tiempo", left + 12, top - 20, (200, 210, 220), 10).draw()
            Text("15:00", left + 12, top - 32, (240, 246, 255), 14, bold=True).draw()

        # Ingresos / Meta - más compacto
        try:
            goal = 1500  # Valor por defecto
            try:
                # Intentar obtener la meta del estado del juego primero
                if hasattr(self.parent.state, "income_goal"):
                    goal = int(self.parent.state.income_goal)
                elif isinstance(self.parent.state, dict) and "income_goal" in self.parent.state:
                    goal = int(self.parent.state["income_goal"])
                else:
                    # Fallback al map_data
                    _m = self.parent.state.get("map_data", {}) if isinstance(self.parent.state, dict) else getattr(self.parent.state, "map_data", {})
                    goal = int((_m or {}).get("goal", 1500))
            except Exception:
                pass
            money = self.parent._get_state_money()
            Text("$ Ingresos / Meta", left + 12, top - 50, (120, 220, 160), 10).draw()
            Text("$" + str(int(money)) + " / $" + str(goal), left + 12, top - 62, (240, 246, 255), 12, bold=True).draw()
        except Exception:
            pass

        # Resistencia con barra - más compacto
        try:
            Text("🔋 Resistencia", left + 12, top - 80, (200, 210, 220), 10).draw()
            stamina = getattr(self.parent.player_stats, "stamina", 100)
            draw_progress_bar(left + 12, top - 88, card_w - 24, 8, stamina / 100.0, (80, 200, 255))
        except Exception:
            pass

        # Reputación con barra - más compacto
        try:
            Text("⭐ Reputación", left + 12, top - 105, (200, 210, 220), 10).draw()
            rep = getattr(self.parent.player_stats, "reputation", 70)
            draw_progress_bar(left + 12, top - 110, card_w - 24, 8, rep / 100.0, (255, 220, 120))
        except Exception:
            pass

        # Peso con barra - más compacto
        try:
            inv = self.parent.state.get("inventory") if isinstance(self.parent.state, dict) else getattr(self.parent.state, "inventory", None)
            weight = float(getattr(inv, "current_weight", 0.0) or 0.0)
            max_weight = 10.0
            Text("📦 Peso", left + 12, top - 130, (200, 210, 220), 10).draw()
            Text(f"{weight:.1f} / {max_weight:.0f} kg", left + 12, top - 142, (230, 236, 245), 10).draw()
            draw_progress_bar(left + 12, top - 150, card_w - 24, 8, weight / max_weight, (255, 180, 100))
        except Exception:
            pass

        # Clima - integrado en la misma ventana, más compacto
        try:
            cond = self.parent.weather.get_current_condition_name()
            clima_text = str(cond)
            Text("☁ Clima", left + 12, top - 165, (200, 210, 220), 10).draw()
            Text(clima_text, left + 12, top - 177, (230, 236, 245), 10).draw()
        except Exception:
            Text("☁ Clima", left + 12, top - 165, (200, 210, 220), 10).draw()
            Text("Despejado", left + 12, top - 177, (230, 236, 245), 10).draw()

        # Indicador de dificultad del CPU y barras propias
        try:
            diff = str(getattr(self.parent, 'cpu_difficulty', 'easy') or 'easy').capitalize()
            Text(f"🤖 CPU: {diff}", left + 12, top - 192, (160, 200, 255), 10).draw()
            # Barras CPU (resistencia / reputación / carga)
            ca = getattr(self.parent, 'cpu_agent', None)
            if ca:
                st = float(getattr(ca, 'stamina', 0.0) or 0.0)
                rp = float(getattr(ca, 'reputation', 0.0) or 0.0)
                try:
                    carry = len(getattr(getattr(ca, 's', None), 'carrying', []) or [])
                    max_c = int(getattr(getattr(ca, 'cfg', None), 'max_carry', 1) or 1)
                except Exception:
                    carry, max_c = 0, 1
                # posiciones bajo clima
                y0 = top - 330
                Text("CPU Resistencia", left + 12, y0, (200, 210, 220), 10).draw()
                draw_progress_bar(left + 12, y0 - 8, card_w - 24, 8, max(0.0, min(1.0, st / 100.0)), (255, 120, 180))
                y1 = y0 - 27
                Text("CPU Reputación", left + 12, y1, (200, 210, 220), 10).draw()
                draw_progress_bar(left + 12, y1 - 8, card_w - 24, 8, max(0.0, min(1.0, rp / 100.0)), (255, 200, 120))
                y2 = y1 - 27
                Text("CPU Carga", left + 12, y2, (200, 210, 220), 10).draw()
                w = 0.0; cap = 10.0
                try:
                    inv = getattr(getattr(ca, 's', None), 'inventory', None)
                    w = float(getattr(inv, 'weight', 0.0) or 0.0)
                    cap = float(getattr(inv, 'capacity_kg', getattr(getattr(ca, 'cfg', None), 'capacity_kg', 10.0)))
                except Exception:
                    pass
                val = 0.0
                try:
                    val = w / float(max(0.01, cap))
                except Exception:
                    val = 0.0
                draw_progress_bar(left + 12, y2 - 8, card_w - 24, 8, max(0.0, min(1.0, val)), (120, 200, 255))
                Text(f"{w:.1f} / {cap:.1f} kg", left + 12, y2 - 22, (230, 236, 245), 10).draw()
                # Lista de inventario del CPU
                y3 = y2 - 48
                Text("CPU Inventario", left + 12, y3, (255, 200, 120), 10).draw()
                # Ingresos / Meta del CPU
                try:
                    cpu_money = float(getattr(getattr(ca, 's', None), 'money', 0.0) or 0.0)
                except Exception:
                    cpu_money = 0.0
                goal = 1500.0
                try:
                    if hasattr(self.parent, 'endgame') and hasattr(self.parent.endgame, '_compute_goal'):
                        goal = float(self.parent.endgame._compute_goal())
                except Exception:
                    pass
                Text(f"$ CPU Ingresos / Meta  ${cpu_money:.0f} / ${goal:.0f}", left + 12, y3 - 12, (160, 255, 180), 10).draw()
                # Lista de inventario con pesos
                items = []
                try:
                    items = list(getattr(inv, 'items', []))
                except Exception:
                    items = []
                if items:
                    for i, jid in enumerate(items[:4]):
                        wt = 0.0
                        try:
                            wt = float(getattr(ca.jobs, 'weight_of')(jid) or 0.0) if hasattr(ca, 'jobs') else 0.0
                        except Exception:
                            wt = 0.0
                        Text(f"- {jid} ({wt:.1f}kg)", left + 12, y3 - 26 - i * 12, (230, 236, 245), 10).draw()
                else:
                    Text("Inventario vacío", left + 12, y3 - 26, (200, 210, 220), 10).draw()
        except Exception:
            pass

    def _draw_inventory_panel(self):
        """Draw the inventory panel with navigation."""
        w = getattr(self.parent, 'SCREEN_WIDTH', self.parent.width)
        h = getattr(self.parent, 'SCREEN_HEIGHT', self.parent.height)
        map_width = getattr(self.parent, 'MAP_WIDTH', 730)

        # Panel de inventario debajo del HUD - más compacto
        panel_w = int(min(350, (w - map_width) * 0.9))
        panel_h = 250  # Reducido
        left = map_width + 10
        top = h - 200  # Más cerca del HUD
        bottom = top - panel_h
        right = left + panel_w

        

        # Título más pequeño
        Text("📦 INVENTARIO", left + 12, top - 20, (255, 220, 120), 12, bold=True).draw()

        # Obtener inventario
        try:
            inv = self.parent.state.get("inventory") if isinstance(self.parent.state, dict) else getattr(self.parent.state, "inventory", None)
            if inv is None:
                Text("No hay inventario disponible", left + 15, top - 50, (200, 200, 200), 12).draw()
                return

            # Obtener lista de items
            items = []
            if hasattr(inv, 'deque') and inv.deque:
                items = list(inv.deque)
            elif hasattr(inv, 'items') and inv.items:
                items = list(inv.items)
            elif hasattr(inv, '__iter__'):
                items = list(inv)

            if not items:
                Text("Inventario vacío", left + 12, top - 45, (200, 200, 200), 10).draw()
                return

            # Navegación
            total_items = len(items)
            if total_items > 0:
                current_item = items[self.parent.inventory_view_index % total_items]

                # Información del item actual - más compacta
                item_id = getattr(current_item, 'id', 'Unknown')
                item_payout = getattr(current_item, 'payout', 0)
                item_weight = getattr(current_item, 'weight', 0)
                item_pickup = getattr(current_item, 'pickup', [0, 0])
                item_dropoff = getattr(current_item, 'dropoff', [0, 0])

                # Mostrar información del item - más compacta
                Text(f"ID: {item_id}", left + 12, top - 40, (240, 246, 255), 10).draw()
                Text(f"Pago: ${item_payout}", left + 12, top - 55, (120, 220, 160), 10).draw()
                Text(f"Peso: {item_weight}kg", left + 12, top - 70, (255, 180, 100), 10).draw()
                Text(f"Recogida: ({item_pickup[0]}, {item_pickup[1]})", left + 12, top - 85, (200, 200, 200), 9).draw()
                Text(f"Entrega: ({item_dropoff[0]}, {item_dropoff[1]})", left + 12, top - 100, (200, 200, 200), 9).draw()

                # Contador de items - más compacto
                Text(f"Item {self.parent.inventory_view_index + 1} de {total_items}", left + 12, top - 120, (180, 196, 220), 10).draw()

                # Botones de navegación - más pequeños
                if total_items > 1:
                    # Botón izquierda
                    btn_w = 50
                    btn_h = 25
                    btn_left = left + 12
                    btn_right = left + 12 + btn_w
                    btn_bottom = top - 160
                    btn_top = btn_bottom + btn_h

                    # Guardar coordenadas para detección de clics
                    self.parent.inventory_left_button_rect = (btn_left, btn_bottom, btn_right, btn_top)

                    _draw_rect_lrbt_filled(btn_left, btn_right, btn_bottom, btn_top, (60, 70, 90))
                    _draw_rect_lrbt_outline(btn_left, btn_right, btn_bottom, btn_top, (100, 120, 140), 1)
                    Text("◀", btn_left + btn_w//2, btn_bottom + btn_h//2, (240, 246, 255), 12,
                         anchor_x="center", anchor_y="center").draw()

                    # Botón derecha
                    btn_left = left + 70
                    btn_right = btn_left + btn_w

                    # Guardar coordenadas para detección de clics
                    self.parent.inventory_right_button_rect = (btn_left, btn_bottom, btn_right, btn_top)

                    _draw_rect_lrbt_filled(btn_left, btn_right, btn_bottom, btn_top, (60, 70, 90))
                    _draw_rect_lrbt_outline(btn_left, btn_right, btn_bottom, btn_top, (100, 120, 140), 1)
                    Text("▶", btn_left + btn_w//2, btn_bottom + btn_h//2, (240, 246, 255), 12,
                         anchor_x="center", anchor_y="center").draw()

                    # Instrucciones - más pequeñas
                    Text("Usa A/D para navegar", left + 12, top - 200, (180, 196, 220), 9).draw()

        except Exception as e:
            Text(f"Error cargando inventario: {str(e)[:30]}", left + 12, top - 50, (255, 120, 120), 10).draw()

    def _draw_undo_button(self):
        """Draw the undo button."""
        if not self.parent.undo_button_visible:
            return

        w = getattr(self.parent, 'SCREEN_WIDTH', self.parent.width)
        h = getattr(self.parent, 'SCREEN_HEIGHT', self.parent.height)

        # Posición del botón justo debajo del botón de menú (arriba derecha)
        btn_w = 100
        btn_h = 35
        btn_left = w - btn_w - 10  # Mismo margen que el botón de menú
        btn_top = h - 10 - btn_h - 10  # Debajo del botón de menú con 10px de separación
        btn_right = btn_left + btn_w
        btn_bottom = btn_top - btn_h

        # Guardar rectángulo para detección de clics
        self.parent.undo_button_rect = (btn_left, btn_bottom, btn_right, btn_top)

        # Fondo del botón (blanco con bordes redondeados simulados)
        _draw_rect_lrbt_filled(btn_left, btn_right, btn_bottom, btn_top, (255, 255, 255))
        _draw_rect_lrbt_outline(btn_left, btn_right, btn_bottom, btn_top, (200, 200, 200), 1)

        # Sombra sutil en la parte inferior
        _draw_rect_lrbt_filled(btn_left, btn_right, btn_bottom - 2, btn_bottom, (180, 180, 180))

        # Icono de deshacer (flecha circular)
        icon_x = btn_left + 12
        icon_y = btn_bottom + btn_h // 2

        # Dibujar flecha circular simple
        arcade.draw_circle_outline(icon_x, icon_y, 6, (0, 0, 0), 2)
        # Flecha apuntando hacia la izquierda
        arcade.draw_line(icon_x - 3, icon_y, icon_x + 1, icon_y - 2, (0, 0, 0), 2)
        arcade.draw_line(icon_x - 3, icon_y, icon_x + 1, icon_y + 2, (0, 0, 0), 2)

        # Texto "Deshacer" más pequeño
        Text("Deshacer", btn_left + 25, btn_bottom + btn_h // 2, (0, 0, 0), 10, bold=True,
             anchor_x="left", anchor_y="center").draw()

    def _draw_endgame_overlay(self):
        """Draw the lose overlay."""
        w = getattr(self.parent, 'SCREEN_WIDTH', self.parent.width)
        h = getattr(self.parent, 'SCREEN_HEIGHT', self.parent.height)
        # fondo semitransparente
        try:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, 180))
        except Exception:
            _draw_rect_lrbt_filled(0, w, 0, h, (10, 10, 14))
        # tarjeta central
        card_w = int(min(520, w * 0.7))
        card_h = 240
        cx = w // 2; cy = h // 2
        left = cx - card_w//2; right = cx + card_w//2
        bottom = cy - card_h//2; top = cy + card_h//2
        _draw_rect_lrbt_filled(left, right, bottom, top, (25, 28, 45))
        _draw_rect_lrbt_outline(left, right, bottom, top, (120, 100, 220), 3)
        title = getattr(self.parent, "_endgame_title", "") or ("❌ Derrota" if getattr(self.parent, "_show_lose_overlay", False) else "Fin del juego")
        title_color = (120, 220, 160) if ("Victoria" in title or "🏆" in title) else (255, 120, 120)
        Text(title, left + 24, top - 40, title_color, 24, bold=True).draw()
        reason = getattr(self.parent, "_endgame_reason", "") or getattr(self.parent, "_lose_reason", "")
        Text(reason, left + 24, top - 70, (230, 236, 245), 14).draw()
        Text("Presiona cualquier tecla para volver al menú principal", left + 24, bottom + 28, (200, 210, 220), 12).draw()
