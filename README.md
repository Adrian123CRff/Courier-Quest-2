# Courier-Quest-2
Segundo avance del proyecto de programacion, Estructura de Datos
## Estructura general del proyecto


- Courier-Quest-2
- Courier-Quest-2/general
- Courier-Quest-2/data
- Courier-Quest-2/resources

+General/ graphics

- ui_view_gui.py Menús principales y flujo de UI
- game_window.py Vista principal del juego
- map_manager.py Gestión de mapa y tiles
- weather_renderer.py Render del clima
- inventory_ui.py Interfaz del inventario
- notification_manager.py Notificaciones en pantalla
- jobs_logic.py Lógica de interacción de trabajos
- money_utils.py Utilidades de dinero
- weather_coordinator.py Coordinación estado/renderer del clima
- coords_utils.py Utilidades de coordenadas
- payout_utils.py Cálculo de pagos
- active_jobs_ui.py UI de trabajos activos
- endgame_manager.py Fin de juego y registro de récords
- save_manager.py Guardado local del estado de la vista
- undo_manager.py Deshacer (fallback UI)
- game_state_manager.py Inicialización y reanudación de sistemas
- input_handler.py Manejo de teclado y mouse
- ui_manager.py Dibujo y control de UI en juego
- update_manager.py Bucle de actualización
- drawing_utils.py Primitivas de dibujo
- 
+General/ game

- game_manager.py Orquestación del juego y reglas
- player_manager.py Movimiento del jugador en celdas
- player_stats.py Stamina y reputación
- weather_markov.py Estado del clima y multiplicadores
- jobs_manager.py Gestión de trabajos aceptados/completados
- inventory.py Inventario sobre Deque
- adts.py Estructuras de datos ( Stack , Deque , Vector , PriorityQueue )
- pathfinding.py Algoritmo A*
- score_system.py Sistema de puntaje (usa scoreboard global)

+General/ run_api

- api_client.py Fuente que valida y cachea datos de la API
- state_initializer.py Construcción de estado inicial de partida
- save_manager.py Guardado/carga de slots .sav + JSON de debug
- saves/slot1.sav Slot 1
- saves/slot2.sav Slot 2
- saves/slot3.sav Slot 3
- saves/debug/slotX.sav.json Snapshots legibles para depuración
data

+General/ ia
-cpu_easy.py
-cpu_medium.py
-cpu_hard.py
-easy_adapters.py


- puntajes.json Records globales persistentes (independientes de los slots)

+Resources
- icons/ Texturas e imágenes 



## Descripciones de Clases:

## Carpeta ia

- cpu_easy.py
  - Propósito: IA fácil que selecciona trabajos al azar, se mueve con sesgo Manhattan hacia pickup/dropoff y ejecuta acciones oportunistas.
  - Algoritmos: generación de vecinos y filtro de transitabilidad; sesgo Manhattan sobre hasta 4 vecinos; tolerancia de adyacencia para pickups/dropoffs.
  - Complejidad: movimiento O(1) por paso; acciones oportunistas O(k) según trabajos en celda; selección de trabajo típicamente O(1).
  - Referencias: general/ia/cpu_easy.py:200 (update), general/ia/cpu_easy.py:248 (_ensure_job_target), general/ia/cpu_easy.py:289 (_random_step), general/ia/cpu_easy.py:345 (_opportunistic_actions)

- cpu_medium.py
  - Propósito: IA media que elige trabajos por una función de valor (payout vs costo aproximado) y avanza de forma codiciosa hacia el objetivo.
  - Algoritmos: scoring lineal por trabajo; distancia Manhattan; selección greedy del mejor vecino con penalización climática.
  - Complejidad: selección O(m) sobre trabajos disponibles; movimiento O(1) por paso; acciones oportunistas O(k).
  - Referencias: general/ia/cpu_medium.py:92 (update), general/ia/cpu_medium.py:131 (_choose_best_job), general/ia/cpu_medium.py:168 (_greedy_step), general/ia/cpu_medium.py:198 (_opportunistic_actions)

- cpu_hard.py
  - Propósito: IA difícil con pathfinding (Dijkstra) y selección de trabajos basada en coste real de ruta hacia pickup y dropoff.
  - Algoritmos: preselección por distancia Manhattan y ordenación; Dijkstra con heap; mantenimiento de camino y avance paso a paso.
  - Complejidad: preselección O(m log m); coste de ruta O(E log V) por candidato (k≤5); movimiento O(1); acciones oportunistas O(k).
  - Referencias: general/ia/cpu_hard.py:85 (update), general/ia/cpu_hard.py:128 (_choose_best_job), general/ia/cpu_hard.py:214 (_dijkstra), general/ia/cpu_hard.py:258 (_ensure_path_to_target), general/ia/cpu_hard.py:282 (_step_along_path), general/ia/cpu_hard.py:305 (_opportunistic_actions)

- easy_adapters.py
  - Propósito: adaptadores entre la IA y sistemas reales de trabajos, clima y mapa (EasyJobsAdapter, EasyWorldAdapter).
  - Algoritmos: filtrado lineal de trabajos (list_available_jobs, get_pickups_at), selección aleatoria, distancia Manhattan y penalización por clima.
  - Complejidad: filtrados O(n) sobre cantidad de trabajos; utilidades O(1); dropoff puede ser O(n) al limpiar inventario humano.


## Carpeta Game

-adts.py

Contiene las estructuras de datos base que el juego utiliza para su lógica interna: una Stack para operaciones LIFO, una Deque para manejar colas y reconstrucciones ordenadas (clave para el inventario y el sistema de deshacer), un Vector como contenedor dinámico simple y una PriorityQueue que apoya la planificación de trabajos según prioridad. Estas abstracciones centralizan el manejo de datos y permiten que módulos como inventario, sistema de trabajos y deshacer funcionen de manera predecible y eficiente.

-api_data_validation_test.py 

Valida la forma y el contenido de datos provenientes de APIs externas antes de que entren al juego. Verifica tipos, campos obligatorios y rangos aceptables para prevenir estados inválidos que podrían romper la simulación (por ejemplo, mapas mal formados, trabajos con coordenadas inexistentes o puntuaciones corruptas). Su propósito es blindar el flujo de datos para que el resto del sistema opere sobre información confiable.

-coords.py

Define el modelo de coordenadas y utilidades para moverse y convertir entre representaciones (por ejemplo, de celda de grilla a coordenadas del mundo y viceversa). Incluye operaciones de dirección (arriba, abajo, izquierda, derecha), vecinos válidos y normalización. Es el cimiento matemático para pathfinding, validación de movimiento y posicionamiento del jugador y objetivos.

-game_manager.py 

Orquesta el ciclo de juego y las transiciones de estado: procesa movimientos, guarda y carga partidas, coordina interacciones entre jugador, mapa, trabajos y clima. Controla cuándo se captura un “snapshot” del estado para el sistema de deshacer (después de aceptar un movimiento válido), sincroniza la puntuación con el sistema global de records y asegura que cada acción se aplique de forma consistente y recuperable.

-integration_test.py

Ejecuta pruebas de integración que simulan flujos completos: iniciar partida, recibir un trabajo, navegar por el mapa, realizar la entrega, afectar reputación y actualizar puntajes. Su rol es verificar que los módulos del juego no solo funcionen aisladamente, sino que se acoplen correctamente, detectando regresiones cuando cambian las piezas principales.

-inventory.py 

Administra el inventario del jugador (tareas pendientes, ítems o paquetes) manteniendo el orden operativo correcto para toma y entrega. Provee operaciones de agregar y retirar, serialización para guardado y restauración consistente durante deshacer. Usa una Deque para preservar el orden real de las tareas, evitando inversiones que generarían estados incoherentes.

-jobs_manager.py 

Gestiona el ciclo de vida de los trabajos (asignación, prioridad, estado en progreso y completado). Emplea una PriorityQueue para priorizar según criterios como distancia, tiempo límite o recompensa, seleccionando el siguiente trabajo óptimo para el jugador. También coordina con el mapa y el estado del jugador para actualizar de manera coherente la disponibilidad y avance de tareas.

-pathfinding.py

Implementa el algoritmo A* para encontrar rutas óptimas entre celdas del mapa usando una heurística Manhattan y un cache de resultados para acelerar consultas repetidas. Reconstruye el camino paso a paso y entrega rutas listas para el sistema de movimiento. Es esencial para la navegación del jugador y el cálculo de rutas de trabajos.

-player_manager.py

Centraliza las acciones de alto nivel del jugador: interpretar comandos de movimiento, solicitar rutas, aplicar pasos sobre el mapa y sincronizar con inventario, estado y estadísticas. Valida colisiones y límites del mapa y prepara los cambios para que el sistema de deshacer pueda revertirlos correctamente. Actúa como “fachada” del comportamiento del jugador frente al resto del juego.

-player_state.py

Modela el estado dinámico del jugador (posición, dirección, flags de movimiento y estados transitorios). Incluye mecanismos para clonar/copiar profundamente el estado, habilitando snapshots robustos para deshacer. Su objetivo es encapsular de forma segura lo que define “dónde y cómo está el jugador” en cada instante.

-player_stats.py

Mantiene estadísticas persistentes del jugador (salud, energía, velocidad, reputación y modificadores), aplicando reglas de progresión o penalizaciones según el rendimiento y las condiciones del entorno. Sirve como base para cálculos que afectan la experiencia del juego más allá de una acción puntual, influyendo en la dificultad y en la recompensa.

-score_system.py

Calcula y registra la puntuación derivada de acciones del jugador (entregas, eficiencia, ruta, penalizaciones). Se integra con un mecanismo de records globales persistente en JSON, separado de los “slots” de guardado de partidas, para que las puntuaciones históricas no bloqueen la creación o sobreescritura de nuevas partidas. Provee lectura/escritura segura y mantiene tablas de records consultables desde el menú.

-undo_system.py 

Mantiene un historial de estados para permitir “deshacer” paso a paso el recorrido del jugador. Solo captura el estado después de movimientos válidos y restituye de manera consistente posición, inventario y banderas, usando Deque para reconstruir el inventario en el orden correcto. Su función es ofrecer retroceso granular: cada pulsación del botón revierte una celda, replicando el camino recorrido en sentido inverso.

-weather_markov.py

Simula el clima mediante una cadena de Markov donde cada estado (soleado, lluvia, viento, etc.) tiene probabilidades de transición hacia otros. El clima afecta condiciones de movimiento, visibilidad y dificultad de trabajos, y puede incorporarse en la planificación y puntuación. Ofrece una evolución estocástica realista y configurable del entorno.


## Carpeta graphics
-active_jobs_ui.py 

Muestra un panel horizontal con los pedidos activos ordenados por urgencia (tiempo restante vs deadline) y alertas visuales cuando están por expirar. Recorre trabajos aceptados y no completados para presentar estado, pago y cronómetros. Usa listas para los pedidos y un conjunto para alertas únicas por job. Complejidad: ordenamiento O(n log n); render O(n) por frame.

-coords_utils.py

Normaliza coordenadas de entrada en distintos formatos (tuplas, diccionarios con varias llaves, cadenas con separadores) y devuelve (x, y) enteros. No emplea estructuras complejas; el parseo es heurístico y con casting. Complejidad: O(1) para tipos numéricos; O(|s|) cuando proviene de texto.

-drawing_utils.py

Provee envoltorios para dibujar rectángulos rellenos y con contorno usando primitivas de Arcade. No introduce algoritmos de búsqueda/ordenamiento ni estructuras de datos. Complejidad: O(1) por llamada de dibujo.

-endgame_manager.py 

Evalúa condiciones de fin (victoria por meta de dinero, derrota por reputación o tiempo), calcula el puntaje considerando dinero y bonus por tiempo restante y registra el resultado en el sistema de puntajes global. Complejidad: cálculo O(1); al guardar se ordena la tabla por score , O(n log n).

-game_state_manager.py 

Inicializa y conecta sistemas (gestor de juego y de trabajos), aplica reanudación de tiempo/clima/posición y siembra trabajos aceptados desde el estado guardado. Usa listas para separar pedidos aceptados y pendientes, conjuntos para filtrar IDs y limpieza del inventario. Complejidad: operaciones principales O(n) sobre trabajos/ítems; consultas en conjuntos O(1).

-game_view.py 

Vista mínima que recibe state , crea GameMap y lo dibuja en modo debug. El render recorre la grilla del mapa. Complejidad: O(w*h).

-game_window.py 

Vista principal que orquesta mapa, jugador, UI, notificaciones, guardado y el loop de actualización. Coordina entradas y subsistemas; por frame recorre trabajos y partículas según elementos activos. Complejidad: típicamente O(n) por frame.

-input_handler.py 

Encapsula manejo de teclado/ratón, mapeando teclas a acciones (mover jugador, navegar inventario, aceptar/rechazar pedidos). Operaciones por evento O(1); puede disparar búsquedas/filtrados en capas lógicas.

-inspect_map_cache.py 

Herramienta de inspección que abre api_cache/city_map.json , muestra resumen y escanea el árbol buscando nodos que parezcan matrices. Complejidad: recorrido recursivo O(N) sobre el JSON; detección por nodo O(1).

-inventory_ui.py 

Dibuja el panel de inventario, obtiene ítems desde distintas estructuras y permite orden por prioridad o deadline, además de paginación. Usa listas y sorted . Complejidad: ordenamientos O(n log n); navegación de páginas O(1).

-jobs_logic.py 

Lógica de pedidos: dibuja pickups/dropoffs, sincroniza dinero con entregas completadas, recomputa totales, gestiona recogida y entrega en función de posición y deadlines. Emplea conjuntos para evitar doble pago en O(1) y recorre trabajos para decisiones. Complejidad: operaciones de pickup/delivery O(n); ordenamientos puntuales O(n log n).

-main_menu.py 

Carga datos iniciales mediante ApiClient , presenta fondo y textos y alterna estados “loading”, “menu” y “playing”. No usa algoritmos intensivos; operaciones de UI y E/S son O(1).

-map_manager.py 

Administra el mapa: define TILE_DEFS y construye la matriz grid . Si hay tiles los normaliza; si faltan, reconstruye a partir de buildings y roads marcando celdas y rectángulos, y puede guardar en caché JSON. Complejidad: reconstrucción O(B+R); dibujo debug O(w*h).

-money_utils.py 

Parsea montos desde múltiples formatos (números y cadenas con símbolos) y actualiza el total en el estado y sistemas relacionados. Usa regex para extraer números y operaciones de suma/propagación. Complejidad: parseo O(|s|); actualización O(1).

-notification_manager.py

Coordina notificaciones temporizadas de pedidos usando tiempo real del juego y release_time . Filtra trabajos disponibles con recorrido lineal y muestra modales para aceptar/rechazar; al aceptar fija accepted_at para cronómetros precisos y añade el job al gestor. Complejidad: filtrado O(n); operaciones por evento O(1).

-notifications.py

Modal gráfico con Arcade GUI para ofertas de pedido y prompt de deshacer. Maneja layouts, botones y callbacks. Complejidad: O(1) por interacción.

-payout_utils.py 

Obtiene el pago de un trabajo inspeccionando múltiples nombres de campo tanto en el objeto como en su raw, normalizando con _parse_money . Recorre un conjunto pequeño de claves (constante). Complejidad: O(1) práctica.

-save_manager.py 

Serializa y deserializa el estado (posición, clima, inventario, trabajos, estadísticas) a archivos .sav. Emplea diccionarios y listas y restaura atributos de forma defensiva. Complejidad: operaciones O(n) según tamaño del estado.

-scoreboard.py 

Tabla de puntajes global en JSON: lee, inserta y ordena por score descendente tras cada nueva entrada. Estructura principal en lista. Complejidad: ordenamiento O(n log n).

-ui_manager.py 

Coordina componentes de UI (paneles, notificaciones, modales) y su ciclo de vida en la vista principal. Opera sobre listas de widgets y flags de visibilidad. Complejidad: por render O(n) según elementos activos; por operación O(1).

-ui_view_gui.py

Vista de menús/slots y elementos GUI. Maneja creación/carga de partidas y binding de eventos por botón; recorre slots para ocupación y registra callbacks. Complejidad: O(n) en inicialización de slots; O(1) por evento.

-undo_manager.py 

Gestiona snapshots de estado para deshacer paso a paso, manteniendo una pila con copias profundas y restaurando posición y banderas del jugador. Complejidad: deepcopy O(1); push/pop O(1); restaurar posición O(1) Complejidad Final O(1).

-update_manager.py

Orquesta el ciclo de actualización: avanza lógica de juego, notificaciones, entrada, pickup/delivery, sincroniza dinero y verifica fin de partida. Recorre trabajos y elementos activos, e invoca ordenamientos puntuales en submódulos. Complejidad: O(n) por frame.

-weather_coordinator.py 

Coordina la actualización del clima: si está congelado, aplica el estado previo al renderer; si no, avanza la cadena de Markov y sincroniza al weather_renderer . Complejidad: O(1) a nivel de coordinación; el coste real depende del render y de la simulación interna.

-weather_renderer.py 

Renderiza efectos climáticos (lluvia, nieve, viento, niebla) y overlays por tile. Mantiene listas de partículas cuya cantidad se ajusta según intensidad; actualizar y dibujar recorren esas listas. Complejidad: O(p) por frame para partículas; overlays por tile O(w*h).


## Carpeta run_api

-api_client.py 

Cliente HTTP con caché en disco y fallbacks robustos. Reutiliza conexiones con requests.Session , guarda respuestas en archivos JSON usando escritura atómica, y decide entre API, caché más reciente, datos locales ( /data ) o valores por defecto según disponibilidad y TTL. Mantiene mapeos de endpoints y genera nombres de caché con parámetros normalizados. Estructuras: diccionarios para datos y configuración, listas de archivos de caché, y rutas ( Path ). Algoritmos: selección del caché más reciente con max sobre tiempos de modificación O(k), validación y filtrado de jobs O(n), construcción de mapas y clima O(1) por campo. Complejidad: fetch con fallback O(k + |file|) sobre número de archivos en caché y tamaño de lectura; validación de trabajos O(n); limpieza de caché O(n).

-debug_api.py 

Utilidad para depurar la estructura real de respuestas de la API. Itera por endpoints, realiza peticiones HTTP, imprime códigos de estado y estructura JSON, y verifica la presencia de campos comunes y del contenedor data . Estructuras: lista de endpoints y diccionarios de respuesta. Algoritmos: ninguno de ordenamiento/búsqueda más allá de comprobaciones directas. Complejidad: O(1) por endpoint más el costo de E/S de red y formateo del JSON.

-game.py

Punto de entrada previsto para la ejecución de juego en el contexto run_api . Actualmente vacío, sirve como placeholder para integrar inicialización de estado, ventana principal y loop del juego. Sin estructuras ni algoritmos implementados.

-models.py

Define el modelo GameState como dataclass serializable con campos para jugador, mapa, pedidos, clima, reputación y dificultad CPU. Provee to_dict y from_dict para normalización y reconstrucción del estado. Estructuras: diccionarios y listas. Algoritmos: conversión de estructuras sin ordenamiento/búsqueda. Complejidad: operaciones O(|state|) al serializar/deserializar según tamaño del estado.

-save_manager.py 

Gestor de guardado/carga de partidas. Normaliza cualquier forma de estado (dict, dataclass, objeto con to_dict ) a un dict, guarda snapshot binario ( pickle ) y un JSON de depuración, y lista partidas disponibles ordenadas por número de slot. Estructuras: diccionarios y listas, rutas. Algoritmos: ordenamiento de nombres de archivos de slots O(n log n); normalización del estado O(|state|); carga y guardado con E/S de archivos O(|file|). Complejidad: guardar/cargar proporcional al tamaño del snapshot; listar y ordenar saves O(n log n).

-state_initializer.py

Inicializa un GameState exclusivamente con datos del API, aplicando fallback de tiles desde caché si el mapa no los trae y completando campos críticos ( start_time , max_time ) con valores por defecto. Integra pedidos y clima en el estado y configura valores de jugador y reputación. Estructuras: diccionarios y listas para datos del mapa y pedidos. Algoritmos: mezcla de diccionarios para completar campos O(|city_map|), escaneo de caché y lectura de JSON O(|file|). Complejidad: inicialización O(n) sobre cantidad de pedidos; fusión de mapa O(|city_map|); operaciones restantes O(1).


## Consumo de stamina
La stamina representa la resistencia del jugador al moverse y realizar acciones. Se consume al desplazarse entre celdas y se recupera cuando el jugador está quieto.

Acción	Costo Base	Detalles:

Movimiento entre celdas	0.5 puntos	Se aplica al completar una celda
Peso en inventario	+0.2 por kg adicional sobre 3 kg	Penalización progresiva
Clima adverso	+0.1–0.3 según condición	Lluvia, viento, tormenta, calor aumentan el costo

El consumo total se calcula como:

costo_total = 0.5 + penalización_peso + penalización_clima

💨 Recuperación de Stamina
Condición	Recuperación	Frecuencia	Requisitos
Jugador quieto (sin input)	+3 %	cada 1 segundo	No presionar teclas de movimiento
En movimiento o con input activo	0 %	—	No se recupera stamina

La recuperación se maneja por acumulación de tiempo mediante un intervalo configurable (RECOVER_INTERVAL = 1.0 s).

⚙ Estados de Stamina
Estado	Rango (%)	Multiplicador de Velocidad	Movimiento Permitido
Normal	> 30	× 1.0	✅ Sí
Cansado	10 – 30	× 0.8	✅ Sí
Exhausto	≤ 0	× 0.0	❌ No

Cuando la stamina alcanza 0 %, el jugador no puede moverse.
Al superar nuevamente 0 %, el movimiento vuelve a estar habilitado.

🎮 Integración con el Juego

El control y actualización de stamina se realiza en la clase PlayerStats.

La clase Player (en player_manager.py) consume stamina al completar el desplazamiento entre celdas.

La clase MapPlayerView (en game_window.py) gestiona la recuperación y sincroniza el estado con el HUD.

💡 Detalles Visuales

La barra de stamina se dibuja en el panel lateral.

Colores según nivel actual:

🟢 Verde 





Cambios al guardar partida
-Ahora, al guardar, se captura un “snapshot” real del estado del juego: posición del jugador, clima, tiempo transcurrido 
y todos los pedidos (pendientes y aceptados) con sus datos clave.
-Al cargar, se rehidrata exactamente ese snapshot: misma celda del jugador, mismo clima, mismo reloj y mismos pedidos, 
respetando sus pickups/dropoffs y sus flags (accepted, picked_up, completed).

Qué se guarda?
-Posición: player_x y player_y (coordenadas de celda).
-Tiempo: elapsed_seconds (segundos transcurridos desde el inicio).
-Clima: weather_state con condition, intensity y multiplier.
-Pedidos (orders/jobs_data): lista deduplicada; cada pedido incluye id, payout, weight, priority, release, deadline, 
pickup, dropoff, accepted, picked_up, completed.
-Bandera de reanudación: resume_from_save = true para indicar que el arranque es una reanudación y no un inicio fresco.

Qué ocurre al cargar?
-Posición: el jugador reaparece en la misma celda guardada.
-Clima: se aplica el estado guardado (y se mantiene estable durante la reentrada inicial).
-Tiempo: no vuelve a cero; se adelanta (“fast-forward”) al elapsed_seconds guardado. Si el GameManager no tiene setters,
se aplica un offset que corrige los getters (get_game_time, get_time_remaining).
-Pedidos aceptados: se vuelven a crear en el JobManager usando sus pickups/dropoffs guardados; si estaban picked_up, 
ya no aparece el punto de recogida y, si tu inventario lo permite, se reinyectan.
-Pedidos pendientes: permanecen en la cola para notificaciones posteriores.

Archivos modificados y propósito
run_api/save_manager.py: guardado (.sav binario y .json de depuración), carga y listado de slots.
graphics/ui_view_gui.py: build_save_snapshot (construye el snapshot), menú de Pausa guarda usando ese snapshot, menú de
Cargar aplica alias de compatibilidad y marca resume_from_save.
graphics/game_window.py (MapPlayerView):
_load_initial_jobs: siembra pedidos aceptados respetando pickup/dropoff del snapshot y restablece accepted/picked_up/completed.
_fast_forward_elapsed: intenta setters; si no hay, usa atributos internos comunes o envuelve getters con offset.

Cómo usar?
-Para guardar: abre el menú de pausa y elige “Guardar”. Se crea el snapshot con posición, clima, tiempo y pedidos tal 
como están en pantalla.
-Para cargar: desde el menú principal, “Cargar Partida” y selecciona el slot. El juego se abrirá con el mismo estado que
tenías al guardar.

Comprobación rápida después de cargar
-El jugador está en la misma celda que al guardar.
-El clima coincide con el guardado.
-El panel de tiempo muestra el transcurrido correcto (no reinicia a 00:00).
-Los pedidos aceptados aparecen activos en el mapa con sus pickups y dropoffs correctos.
-Los pedidos que ya estaban recogidos no muestran el punto de recogida.

Problemas típicos y solución
-“Solo reaparece un pedido”: asegúrate de tener el _load_initial_jobs que usa pickup/dropoff del snapshot y no la 
posición del jugador; también fuerza las flags accepted/picked_up/completed del guardado.
-“El tiempo inicia en 0”: confirma que _fast_forward_elapsed esté reemplazado. Si tu GameManager usa nombres internos
distintos para el tiempo, ajusta el bloque de atributos internos (por ejemplo, _elapsed vs elapsed).
-“Un pedido recogido vuelve a mostrar PICKUP”: verifica que build_save_snapshot está incluyendo picked_up y 
que _load_initial_jobs lo aplica al JobManager.

Nota sobre JobManager
-Si add_job_from_raw no acepta parámetro de “spawn hint”, pásale None. Lo importante es que, después de crear el job, 
-se fuerzan job.pickup y job.dropoff con los valores del snapshot para que no se muevan a la celda del jugador.

Proyecto que simula la gestión de trabajos/entregas en un mapa (pickup, dropoff, inventario, tiempo simulado, sistema de puntuación y UI). El código incluye implementaciones propias de estructuras de datos lineales y varios subsistemas (gestor de trabajos, inventario, pathfinding, clima, undo, etc.). Este README explica qué estructuras de datos se usaron, dónde se usan y la complejidad algorítmica relevante.

## Estructuras de datos implementadas (y por qué)


El proyecto utiliza diversas estructuras de datos para sostener su lógica y rendimiento. En el núcleo, adts.py define abstracciones como Stack , Deque , Vector y PriorityQueue : las operaciones básicas en Stack y Deque son O(1), las inserciones en Vector son amortizadas O(1), y en PriorityQueue tanto insertar como extraer tienen costo O(log n). Estas estructuras se reflejan en jobs_manager.py , que agenda trabajos con una cola de prioridad (inserciones/extracciones O(log n), filtrado de disponibles O(n)), y en inventory.py , que mantiene los ítems en una Deque con operaciones de agregar/quitar O(1) y recorridos O(n). El sistema de deshacer ( undo_system.py ) gestiona un historial con pila o deque: push/pop O(1) y restauraciones dependientes del tamaño del estado O(|state|). Para navegación, pathfinding.py implementa A* con una heap y diccionarios de costos; el costo de expansión típico es O(b^d) y cada operación de heap por nodo es O(log n). La evolución del clima en weather_markov.py usa diccionarios para el estado y transiciones con pasos O(1), mientras score_system.py acumula métricas en O(1) y ordena rankings con O(n log n). Utilidades de coordenadas ( coords.py ) normalizan entradas en O(1) cuando son numéricas y O(|s|) al parsear cadenas.

En la capa gráfica y de interfaz, active_jobs_ui.py y inventory_ui.py trabajan con listas para mostrar y ordenar elementos: la presentación recorre O(n) por cuadro y los ordenamientos por urgencia o prioridad son O(n log n); la paginación usa slicing e índices O(1). La lógica de pedidos ( jobs_logic.py ) realiza búsquedas lineales O(n) para pickups y dropoffs, utiliza conjuntos para evitar pagos duplicados en O(1), y recalcula totales en O(n). La gestión del mapa ( map_manager.py ) se apoya en una grilla (lista de listas) y un diccionario de definiciones ( TILE_DEFS ); reconstruir desde buildings y roads es O(B+R), normalizar filas es O(rows cols) y dibujar el mapa completo en debug es O(w h). El renderer de clima ( weather_renderer.py ) mantiene listas de partículas, y su actualización/dibujo por cuadro es O(p), además de aplicar overlays por tile O(w*h). La coordinación de notificaciones ( notification_manager.py ) filtra trabajos disponibles en O(n) y opera estados en O(1). La tabla de puntajes ( scoreboard.py ) almacena entradas en una lista y ordena por score en O(n log n). El gestor gráfico de deshacer ( undo_manager.py ) opera una pila con push/pop O(1) y restauraciones O(|state|), y el gestor gráfico de guardado ( save_manager.py ) serializa/deserializa estados en O(n). Utilidades como payout_utils.py realizan búsquedas de campos de pago en conjuntos de claves constantes (O(1) práctico) y money_utils.py parsea montos mediante expresiones regulares en O(|s|) y actualiza acumulados en O(1).

En la capa de API, caché y estado, api_client.py decide entre datos del API, caché más reciente, archivos locales o valores por defecto. Seleccionar el caché más reciente recorre archivos y aplica max sobre tiempos de modificación (O(k)), validar y filtrar trabajos es O(n), limpiar caché es O(k), y mezclar mapas es O(|city_map|). El gestor de guardado en run_api/save_manager.py normaliza estados a diccionario en O(|state|), guarda/carga snapshots con E/S O(|file|), y lista/ordena slots en O(n log n). El inicializador ( state_initializer.py ) integra datos del API y aplica fallback de tiles desde caché con lectura/mezcla O(|file| + |city_map|) y construcción del estado con integración de pedidos O(n). El modelo GameState en models.py serializa y deserializa estructuras con costos proporcionales al tamaño del estado O(|state|). En conjunto, las estructuras de datos se aplican de forma consistente para mantener operaciones críticas en O(1) donde importa, ordenamientos en O(n log n) cuando es necesario priorizar, y recorridos lineales O(n) en pipelines de render y lógica por cuadro.







Las implementaciones se encuentran en `adts.py`:

Stack (pila LIFO)  
  Operaciones: `push`, `pop`, `peek`, `is_empty`.  
  Justificación: control de historial/undo (UndoSystem guarda snapshots usando una pila).
  Complejidad: `push` O(1) amortizado, `pop` O(1), `peek` O(1).

Queue (buffer circular, FIFO)  
  Implementada con búfer circular y re-alloc cuando se llena.  
  Justificación: colas temporales y prequeue en sistemas (p. ej. WeatherMarkov prequeue). 
  Complejidad: `enqueue` O(1) amortizado (crecimiento ocasional O(n)), `dequeue` O(1).

Deque (lista doblemente enlazada)  
  Operaciones: `append`, `appendleft`, `pop`, `popleft`, `remove_node`, iterador, etc.  
  Justificación: inventario implementado sobre una Deque para permitir inserciones/eliminaciones eficientemente en ambos extremos y eliminación de nodos concretos. 
  Complejidad: operaciones de extremos O(1); `remove_node` O(1) si ya tienes la referencia al nodo; búsqueda de un valor por id (recorrido) O(n).

Vector (wrapper de array dinámico)  
  API mínima: `push`, `pop`, `get`, `set`, `to_list`.  
  Justificación: envoltorio simple para uso genérico cuando se requiere acceso por índice.
  Complejidad: `push` O(1) amortizado, `pop` O(1), `get`/`set` O(1).

PriorityQueue (min-heap con soporte update/remove perezoso)  
  Implementación: heap (`heapq`) + `entry_finder` + marca `REMOVED` para eliminaciones perezosas.  
  Justificación: Gestión de prioridad de trabajos y estructuras similares. `JobManager` usa un heap de prioridades para jobs (prioridad + release_time). 
  Complejidad: `push` O(log n), `pop` O(log n) amortizado (omite entradas marcadas), `remove` marca la entrada (O(log n) para `heappush` del marcador), `peek` amortizado (puede limpiar marcadores => costo extra amortizado).

## Dónde se usan (mapa rápido de archivos)
`game/adts.py` — implementaciones de Stack, Queue, Deque, Vector, PriorityQueue. 
`inventory.py` — inventario construido sobre `Deque`, métodos públicos para obtener valores y ordenar (`get_deque_values`, `sort_by_priority`, `sort_by_deadline`).
`jobs_manager.py` — `JobManager` mantiene `Job` y un heap con tuplas `(-priority, release_time, counter, job_id)` para selección de trabajos. Usa `heapq`. 
`pathfinding.py` — implementación A sobre cuadrícula con `heapq` (open set como heap), `manhattan` como heurística. Usado por IA/planificación de rutas. 
`undo_system.py` — usa `Stack` para snapshots/undo. 
`game_manager.py`, `player_state.py`, `player_manager.py`, `score_system.py` — integran y consumen las estructuras anteriores. (ver fuentes para detalles). 

## Complejidad algorítmica — operaciones y algoritmos clave

### Operaciones básicas (DS)
Stack: push/pop/peek = O(1).  
Queue (circular): enqueue/dequeue = O(1) amortizado (crecimiento O(n) ocasional).  
Deque (DLL): append/appendleft/pop/popleft = O(1). `remove_node` = O(1) si se tiene la referencia; buscar por valor o id = O(n).  
Vector (array dinámico): push amortizado O(1), pop O(1), get/set O(1), iteración O(n).  
PriorityQueue (heap + entry_finder): push O(log n), pop O(log n) amortizado, lazy remove O(log n) (por push de marcador), peek amortizado.

### JobManager — heap y selección de jobs
`JobManager` mantiene un heap con entradas `(-priority, release_time, counter, job_id)` para priorizar por `priority` y por `release_time`.  
`add_job_from_raw`: inserción en heap O(log n).  
`peek_next_eligible(now)`: implementado sacando elementos del heap hasta encontrar uno elegible y luego reinserta los extraídos.  
  Costo: en el peor caso puede inspeccionar k entradas y cada extracción/reinserción cuesta O(log n) → O(k log n). En el peor caso k ≈ n => O(n log n). Sin embargo, en uso típico k suele ser pequeño (los jobs inactivos se reinsertan). :contentReference[oaicite:18]{index=18}

### A en `pathfinding.py`
Implementación A con `heapq`, `gscore` y heurística Manhattan.  
Complejidad: en grafos generales A puede costar O(|E| + |V| log |V|) si se usan montículos y estructuras adecuadas; para cuadrícula con V celdas la complejidad práctica suele acercarse a O(V log V) en la peor caso. La heurística admisible (Manhattan) reduce considerablemente la expansión en la práctica. :contentReference[oaicite:20]{index=20}

### Ordenaciones en inventario
`Inventory.sort_by_priority()` y `sort_by_deadline()` usan `list.sort()` de Python sobre la lista serializada del deque.  
  Complejidad: O(m log m) donde m = número de items en inventario.

