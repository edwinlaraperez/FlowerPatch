import os
from datetime import datetime
import numpy as np
import pandas as pd
import importlib
import Forage
from Agent import HoneyBee
from itertools import product

# ———————————————————————————————————————————————————————————————————
# Recarga módulo para asegurar los últimos cambios en Forage
# ———————————————————————————————————————————————————————————————————
importlib.reload(Forage)
from Forage import Forage

# ———————————————————————————————————————————————————————————————————
# Parámetros generales de la simulación
# ———————————————————————————————————————————————————————————————————
Time_sim        = 5000
resource_value  = 1

# Rango de valores para cada parámetro
Nexplorer_range  = [3, 5, 10, 20]
Nexploiter_range = [3, 5, 10, 20]
dist_colony_range = [50, 100, 130, 150]
speed_x_range    = [5, 10, 15, 20, 40]
speed_y_range    = [5, 10, 15, 20, 40]
n_range          = [4, 6, 7, 8]
d_x_range        = [1, 2, 4, 6]
d_y_range        = [1, 2, 4, 6]

# Crear carpeta principal con timestamp
timestamp   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
base_folder = f"Sim_{timestamp}"
os.makedirs(base_folder, exist_ok=True)

# Coordenadas fijas de la colmena (hive)
hive_x, hive_y = HoneyBee.hiveX, HoneyBee.hiveY

# ———————————————————————————————————————————————————————————————————
# Bucle sobre todas las combinaciones de parámetros
# ———————————————————————————————————————————————————————————————————
for (Nexplorer, Nexploiter,
     dist_colony,
     speed_x, speed_y,
     n, d_x, d_y) in product(
        Nexplorer_range, Nexploiter_range,
        dist_colony_range,
        speed_x_range, speed_y_range,
        n_range, d_x_range, d_y_range
    ):

    # Definir zona de recursos a la distancia deseada
    target_zone = (hive_x + dist_colony, hive_y)

    # Lista para almacenar registros de cada paso
    rows = []

    # —————————————————————————————————————————————————————————————————
    # Inicializar simulación
    # —————————————————————————————————————————————————————————————————
    sim = Forage(
        Nexplorer=Nexplorer,
        Nexploiter=Nexploiter,
        T=Time_sim,
        SctPersistence=20,
        RecPersistence=25
    )
    sim.resourcesMatrixSpacing(
        n=n, d_x=d_x, d_y=d_y,
        resource_value=resource_value,
        start_x=target_zone[0] + 2,
        start_y=target_zone[1] - 1
    )
    # Asignar colmena y capacidad
    for bee in sim.Explorers + sim.Exploiters:
        bee.target   = target_zone
        bee.capacity = 2

    # Velocidades de reposición
    sim.speed_x = speed_x
    sim.speed_y = speed_y

    # Reiniciar contador de néctar recolectado
    sim.total_collected = 0

    # —————————————————————————————————————————————————————————————————
    # Ejecutar la simulación paso a paso
    # —————————————————————————————————————————————————————————————————
    for step in range(Time_sim):
        prev_len = len(sim.visitLog)
        sim.update()
        new_events  = sim.visitLog[prev_len:]
        visitas_con = sum(1 for ev in new_events if ev[0] == 'visita_con_recurso')
        visitas_sin = sum(1 for ev in new_events if ev[0] == 'visita_sin_recurso')
        queue_wait  = sum(wait for (_, _, wait) in sim.flowerQueue)
        collected   = sim.total_collected

        rows.append({
            'd_x':         d_x,
            'd_y':         d_y,
            'speed_x':     speed_x,
            'speed_y':     speed_y,
            'dist_colony': dist_colony,
            'Nexpl':       Nexplorer,
            'Nexploit':    Nexploiter,
            'n':           n,
            'step':        step,
            'visitas_con': visitas_con,
            'visitas_sin': visitas_sin,
            'queue_wait':  queue_wait,
            'collected':   collected
        })

    # —————————————————————————————————————————————————————————————————
    # Guardar CSV de resumen de esta simulación
    # —————————————————————————————————————————————————————————————————
    filename = (
        f"resumen_dx{d_x}_dy{d_y}_n{n}"
        f"_sx{speed_x}_sy{speed_y}"
        f"_explr{Nexplorer}_explt{Nexploiter}"
        f"_dist{dist_colony}.csv"
    )
    filepath = os.path.join(base_folder, filename)
    pd.DataFrame(rows).to_csv(filepath, index=False)

    print(f"Guardado: {filepath}")

print(f"\nTodas las simulaciones han terminado.\n"
      f"Archivos guardados en carpeta: {base_folder}/")
