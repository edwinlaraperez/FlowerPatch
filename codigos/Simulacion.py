import numpy as np
import pandas as pd
import importlib
import Forage
from Agent import HoneyBee
from matplotlib.animation import FFMpegWriter
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# Recarga módulo para asegurar los últimos cambios
importlib.reload(Forage)
from Forage import Forage

# ———————————————————————————————————————————————————————————————————
# PARÁMETROS DE SIMULACIÓN
# ———————————————————————————————————————————————————————————————————
Time_sim      = 1500
Nexplorer     = 10
Nexploiter    = 10
n             = 6
d_x           = 1
d_y           = 1
resource_value = 1

# Centro del flower-patch y zona objetivo
target_zone = (172, 249)


# ———————————————————————————————————————————————————————————————————
# INICIALIZAR SIMULACIÓN
# ———————————————————————————————————————————————————————————————————
sim = Forage(Nexplorer=Nexplorer, Nexploiter=Nexploiter, T=Time_sim,SctPersistence=20,RecPersistence=25)
sim.resourcesMatrixSpacing(
    n=n, d_x=d_x, d_y=d_y, resource_value=resource_value,
    start_x=target_zone[0] + 2,
    start_y=target_zone[1] - 1
)

# Asignar target y capacidad a cada abeja
for bee in sim.Explorers + sim.Exploiters:
    bee.target   = target_zone
    bee.capacity = 2

# Velocidades de recarga
sim.speed_x = 2
sim.speed_y = 2

# Reiniciar contador de néctar
sim.total_collected = 0

# Distancia colmena–flowerpatch (euclidiana)
hive_x, hive_y    = HoneyBee.hiveX, HoneyBee.hiveY
dist_colony       = np.hypot(hive_x - target_zone[0],
                            hive_y - target_zone[1])

# ———————————————————————————————————————————————————————————————————
# PREPARAR STRUCTURA DE DATOS
# ———————————————————————————————————————————————————————————————————
rows = []   # Lista de diccionarios que luego irá a DataFrame

# ———————————————————————————————————————————————————————————————————
# PREPARAR VIDEO
# ———————————————————————————————————————————————————————————————————
fig = plt.figure(figsize=(18, 10))
gs  = gridspec.GridSpec(2, 3, figure=fig)
ax_sim      = fig.add_subplot(gs[0, :2])
ax_zoom     = fig.add_subplot(gs[0, 2])
ax_hist     = fig.add_subplot(gs[1, 0])
ax_resource = fig.add_subplot(gs[1, 1])
ax_queue    = fig.add_subplot(gs[1, 2])

writer       = FFMpegWriter(fps=15, metadata=dict(artist='ABBAS Simulation'), bitrate=10000)
output_video = 'flowerpatch_simulation.mp4'

with writer.saving(fig, output_video, dpi=300):
    for step in range(Time_sim):
        # 1) Capturar visitas del paso
        prev_len = len(sim.visitLog)
        sim.update()
        new_events = sim.visitLog[prev_len:]
        visitas_con = sum(1 for ev in new_events if ev[0] == 'visita_con_recurso')
        visitas_sin = sum(1 for ev in new_events if ev[0] == 'visita_sin_recurso')

        # 2) Cola de espera y néctar total
        queue_wait = sum(wait for (_, _, wait) in sim.flowerQueue)
        collected  = sim.total_collected

        # 3) Almacenar fila
        rows.append({
            'd_x':         d_x,
            'd_y':         d_y,
            'speed_x':     sim.speed_x,
            'speed_y':     sim.speed_y,
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

        # ——— GRAFICOS PARA VIDEO ———

        # Exportar posiciones y estado del patch
        sctPos, recPos, _ = sim.exportBeePositions()
        res_x, res_y      = np.nonzero(sim.Area)

        # Simulación completa
        ax_sim.clear()
        ax_sim.scatter(sctPos[0], sctPos[1], color='red',   label='Scouts')
        ax_sim.scatter(recPos[0], recPos[1], color='blue',  label='Recruits')
        ax_sim.scatter(res_x,    res_y,    color='green', marker='o', s=10, label='Patch')
        ax_sim.scatter(hive_x,   hive_y,   color='#B8860B', marker='^', s=250, label='Hive')
        ax_sim.set_xlim(0, sim.Lx)
        ax_sim.set_ylim(0, sim.Ly)
        ax_sim.set_title('Simulación completa')
        ax_sim.legend(loc='upper right')

        # Zoom en flower-patch
        ax_zoom.clear()
        ax_zoom.scatter(sctPos[0], sctPos[1], color='red',  label='Scouts')
        ax_zoom.scatter(recPos[0], recPos[1], color='blue', label='Recruits')
        ax_zoom.scatter(res_x,    res_y,    color='green', marker='o', s=20, label='Patch')
        ax_zoom.scatter(hive_x,   hive_y,   color='#B8860B', marker='^', s=250, label='Hive')
        ax_zoom.set_xlim(target_zone[0] - 20, target_zone[0] + 40)
        ax_zoom.set_ylim(target_zone[1] - 20, target_zone[1] + 40)
        ax_zoom.set_title('Acercamiento FP')
        ax_zoom.legend(loc='upper right')

        # Histograma de visitas acumuladas
        ax_hist.clear()
        total_con = sum(1 for v in sim.visitLog if v[0] == 'visita_con_recurso')
        total_sin = sum(1 for v in sim.visitLog if v[0] == 'visita_sin_recurso')
        ax_hist.bar(['Con recurso', 'Sin recurso'], [total_con, total_sin])
        ax_hist.set_title('Visitas acumuladas')
        ax_hist.set_ylabel('Cantidad')

        # Recurso acumulado
        ax_resource.clear()
        collected_series = [row['collected'] for row in rows]
        ax_resource.plot(collected_series, 'b-')
        ax_resource.set_title('Néctar recolectado')
        ax_resource.set_xlabel('Paso')
        ax_resource.set_ylabel('Unidades')

        # Tiempo total en cola
        ax_queue.clear()
        queue_series = [row['queue_wait'] for row in rows]
        ax_queue.plot(queue_series, 'm-')
        ax_queue.set_title('Espera total en cola')
        ax_queue.set_xlabel('Paso')
        ax_queue.set_ylabel('Suma waiting_steps')

        writer.grab_frame()
        print(step)
print(f"Video guardado en: {output_video}")

# ———————————————————————————————————————————————————————————————————
# EXPORTAR DATASET
# ———————————————————————————————————————————————————————————————————
df = pd.DataFrame(rows)
df.to_csv('flowerpatch_dataset.csv', index=False)
print("Dataset guardado en 'flowerpatch_dataset.csv'")
