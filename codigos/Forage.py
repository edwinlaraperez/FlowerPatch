import numpy as np
import pylab as pl
import random
from math import *
import importlib
import Agent
importlib.reload(Agent)
from Agent import HoneyBee

class Forage:

    def __init__(self, Nexplorer=5, Nexploiter=100, T=1500,
                 SctPersistence=10, RecPersistence=15):
        self.NBeesTotal = Nexplorer + Nexploiter
        self.total_collected = 0
        # Área de simulación
        self.Lx = 500
        self.Ly = 500

        # Matriz de recursos, inicializada en 0
        self.Area = np.zeros((self.Lx, self.Ly), dtype=int)
        self.RescMax = 50

        # Lista para guardar visitas: (tipo, tiempo, x, y)
        self.visitLog = []

        # Crear abejas exploradoras
        self.Nexplorers = Nexplorer
        self.Explorers = []
        for j in range(self.Nexplorers):
            bee = HoneyBee(0, 0, self.Lx/2, self.Ly/2,
                           v=1.5, tsigma=5., persistence=SctPersistence)
            bee.Hive = self
            self.Explorers.append(bee)

        # Crear abejas explotadoras
        self.Nexploiters = Nexploiter
        self.Exploiters = []
        for j in range(self.Nexploiters):
            bee = HoneyBee(1, 1, self.Lx/2, self.Ly/2+2,
                           v=1.0, tsigma=2., persistence=RecPersistence)
            bee.Hive = self
            self.Exploiters.append(bee)

        # Posición de la colmena
        self.Explorers[0].updateHivePosition([self.Lx/2, self.Ly/2])
        self.Nrecruiteds = 0

        # Diccionario para posiciones broadcast.
        self.broadcastedPositions = {}

        # Log de características por tiempo
        Nfeatures = 5
        self.Log = np.zeros((T, Nfeatures))
        self.t = 0

        # Parámetros para el bloque de recursos (flower patch)
        self.block_start_x = None
        self.block_start_y = None
        self.block_n = None
        self.block_d_x = None
        self.block_d_y = None

        # Parámetros para la velocidad de reposición (función de coste)
        self.speed_x = 10.0  # Unidades de coste en X
        self.speed_y = 10.0  # Unidades de coste en Y

        # Cola para flores a repoblar: lista de tuplas (x, y, waiting_steps)
        self.flowerQueue = []
        self.replenisher_position = None

        # Umbrales
        self.dead_time = 2500
        self.scout_switch_threshold = 1500

        # Tiempos de reposición (t0) de cada flor
        self.flowerTimes = {}

    def qualityNectar(self):
        """
        Calcula la calidad del néctar usando un modelo JMAK:
          quality = 4 * exp(-C * (t - t0)^alpha)
        """
        C = 0.019005956324516033
        alpha = 0.6631653771232885
        qualities = []
        for (x, y), t0 in self.flowerTimes.items():
            dt = self.t - t0
            qualities.append(4 * np.exp(-C * dt**alpha))
        return round(np.mean(qualities), 3) if qualities else 4


    def resourcesMatrixSpacing(self, n, d_x, d_y, resource_value=1, start_x=None, start_y=None):
        #start_x = 200
        #start_y = (self.Ly - (n - 1) * d_y) // 2
        self.block_start_x = start_x
        self.block_start_y = start_y
        self.block_n = n
        self.block_d_x = d_x
        self.block_d_y = d_y
        self.flowerQueue = []
        self.replenisher_position = [start_x, start_y]
        self.flowerTimes = {}
        for i in range(n):
            for j in range(n):
                x = int(start_x + i * d_x)
                y = int(start_y + j * d_y)
                self.Area[x, y] = resource_value
                self.flowerTimes[(x, y)] = self.t
        return

    def regenerateNectar(self):
        if not self.flowerQueue:
            return
        decrement = 1
        newQueue = [(x, y, steps-decrement) for (x, y, steps) in self.flowerQueue]
        if newQueue and newQueue[0][2] <= 0:
            x, y, _ = ready = newQueue.pop(0)
            self.Area[x, y] = 1
            self.replenisher_position = [x, y]
            self.flowerTimes[(x, y)] = self.t
            if newQueue:
                adjust = ready[2]
                newQueue = [(x, y, steps+abs(adjust)) for (x, y, steps) in newQueue]
        self.flowerQueue = newQueue
        return

    def update(self):
        # Exploradoras
        for bee in self.Explorers:
            bee.update()
            pos_x, pos_y = int(bee.x), int(bee.y)
            # Registro de visita
            if (pos_x, pos_y) in self.flowerTimes:
                if self.Area[pos_x, pos_y] > 0:
                    self.visitLog.append(('visita_con_recurso', self.t, pos_x, pos_y))
                else:
                    self.visitLog.append(('visita_sin_recurso', self.t, pos_x, pos_y))
            # Consumo
            if (bee.mode == 0 or bee.mode == -3) and self.Area[pos_x, pos_y] > 0 and bee.nectar < bee.capacity:
                bee.foundSpot()
                self.Log[self.t, 0] += 1
                self.Area[pos_x, pos_y] -= 1
                # Manejo de cola
                if self.Area[pos_x, pos_y] == 0:
                    if not self.flowerQueue:
                        base = self.replenisher_position or (self.block_start_x, self.block_start_y)
                        cost = (abs(pos_x-base[0])*self.speed_x + abs(pos_y-base[1])*self.speed_y) + 4
                        wait = int(ceil(cost/1.2))
                    else:
                        last = self.flowerQueue[-1]
                        cost = (abs(pos_x-last[0])*self.speed_x + abs(pos_y-last[1])*self.speed_y) + 4
                        wait = last[2] + int(ceil(cost/1.2))
                    self.flowerQueue.append((pos_x, pos_y, wait))
            self.Log[self.t, 2] += bee.energy

        # Explotadoras (recolectoras)
        for bee in self.Exploiters:
            bee.update()
            pos_x, pos_y = int(bee.x), int(bee.y)
            # Registro de visita
            if (pos_x, pos_y) in self.flowerTimes:
                if self.Area[pos_x, pos_y] > 0:
                    self.visitLog.append(('visita_con_recurso', self.t, pos_x, pos_y))
                else:
                    self.visitLog.append(('visita_sin_recurso', self.t, pos_x, pos_y))
            # Consumo
            if (bee.mode == 0 or bee.mode == -3) and self.Area[pos_x, pos_y] > 0 and bee.nectar < bee.capacity:
                bee.foundSpot()
                self.Area[pos_x, pos_y] -= 1
                if self.Area[pos_x, pos_y] == 0:
                    if not self.flowerQueue:
                        base = self.replenisher_position or (self.block_start_x, self.block_start_y)
                        cost = abs(pos_x-base[0])*self.speed_x + abs(pos_y-base[1])*self.speed_y
                        wait = int(ceil(cost/1.2))
                    else:
                        last = self.flowerQueue[-1]
                        cost = abs(pos_x-last[0])*self.speed_x + abs(pos_y-last[1])*self.speed_y
                        wait = last[2] + int(ceil(cost/1.2))
                    self.flowerQueue.append((pos_x, pos_y, wait))
            self.Log[self.t, 3] += bee.energy

        # Estadísticas y reclutamiento
        Nrecruiteds_tmp = sum(1 for bee in self.Exploiters if bee.mode <= 0)
        self.Nrecruiteds = Nrecruiteds_tmp
        self.Log[self.t, 4] = float(self.Nrecruiteds) / self.Nexploiters

        # Incrementa tiempo y regenera néctar
        self.t += 1
        self.regenerateNectar()
        #print(f"Flower Queue at step {self.t}: {self.flowerQueue}")

        # Revisa inactividad
        for bee in self.Explorers + self.Exploiters:
            if bee.mode in (0, -3):
                bee.steps_without_resource += 1
                if bee in self.Explorers and bee.steps_without_resource >= self.scout_switch_threshold and bee.nectar < bee.capacity:
                    #print(f"Scout {bee.BeeId} switching to random exploration after {bee.steps_without_resource} steps without resource.")
                    bee.mode = 0
                    bee.new_drift_vector()
                    bee.steps_without_resource = 0
                elif bee in self.Exploiters and bee.steps_without_resource >= self.dead_time:
                    #print(f"Recruit {bee.BeeId} eliminated by inactivity ({bee.steps_without_resource} steps without resource). Remains in hive.")
                    bee.x, bee.y = HoneyBee.hiveX, HoneyBee.hiveY
                    bee.nectar = 0
                    bee.steps_without_resource = 0
                    bee.mode = 1
        return

    def addFood(self):
        self.Log[self.t, 1] += 1
        self.total_collected += 3
        return

    def picture(self, hl0, hle0, hl1):
        x, y = zip(*[(bee.x, bee.y) for bee in self.Exploiters])
        hl0.set_xdata(x); hl0.set_ydata(y)
        x, y = zip(*[(bee.x, bee.y) for bee in self.Explorers])
        hle0.set_xdata(x); hle0.set_ydata(y)
        areaPos = np.nonzero(self.Area)
        hl1.set_xdata(areaPos[0]); hl1.set_ydata(areaPos[1])
        return

    def exportBeePositions(self):
        SctPos = [[bee.x for bee in self.Explorers], [bee.y for bee in self.Explorers]]
        RecPos = [[bee.x for bee in self.Exploiters], [bee.y for bee in self.Exploiters]]
        areaPos = np.nonzero(self.Area)
        return SctPos, RecPos, areaPos

if __name__ == "__main__":
    print('as a starting point')
