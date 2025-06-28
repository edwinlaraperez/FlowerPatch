import numpy as np
from numpy import linalg as la
import random
from math import *

class HoneyBee:
    """
    mode:
      -2 = Dancing, dancing...
      -1 = Explorer returning to hive
       0 = Exploring
       1 = Exploiter waiting
       2 = Exploiter recruited
    """

    hiveX = 250
    hiveY = 250

    timeWagDance = 50
    Nbees = 0
    Krecruitment = 0.1
    dE_a = 1e-5
    dE_b = 1e-6

    def __init__(self, bclass, mode, x0, y0, Lx=200, Ly=200, v=1.5,
                 tsigma=0.2, persistence=10, capacity=10, target=None):
        self.BeeId = HoneyBee.Nbees
        HoneyBee.Nbees += 1

        self.x = x0
        self.y = y0
        self.bclass = bclass
        self.mode = mode
        self.spot = []
        self.Hive = None
        self.energy = 0.
        self.v = v
        self.v_explore = v
        self.v_exploit = 1.0
        self.tsigma = tsigma
        self.tsigma_explore = tsigma
        self.tsigma_exploit = 0.2
        self.recruitedSpot = []
        self.wagdance_t = 0
        self.persistence = persistence
        self.nectar = 0
        self.capacity = capacity
        self.steps_without_resource = 0
        self.target = target if target is not None else (152, 249)

        if self.bclass == 0:
            self.update = self.move
            self.updatePos = self.DriftRandomWalk
            self.Returned = self.explorerReturned
            self.new_drift_vector()
            self.returnCount = 0
        elif self.bclass == 1:
            self.update = self.Recruitment
            self.updatePos = self.exploiterWalk
            self.Returned = self.exploiterReturned
            self.returnCount = 0
        return

    def updatePersistence(self, RT):
        self.persistence = RT
        return

    def updateHivePosition(self, Pos):
        HoneyBee.hiveX = Pos[0]
        HoneyBee.hiveY = Pos[1]
        return

    def updateWagDanceDuration(self, T):
        self.timeWagDance = T
        return

    def updateHAvgRecruitment(K):
        HoneyBee.Krecruitment = K
        return

    def foundSpot(self):
        pos = np.array([self.x, self.y])
        hive_pos = np.array([HoneyBee.hiveX, HoneyBee.hiveY])
        if la.norm(pos - hive_pos) > 5.0:
            self.spot = [int(self.x), int(self.y)]
        self.steps_without_resource = 0
        if self.nectar < self.capacity:
            self.nectar += 1
            if self.nectar >= self.capacity:
                self.mode = -1
        return

    def move(self, scale=3):
        if self.mode == 0 or self.mode == -3:
            self.updatePos()
        elif self.mode == -1:
            if int(abs(self.x - HoneyBee.hiveX)) < 3 and int(abs(self.y - HoneyBee.hiveY)) < 3:
                self.Returned()
            else:
                cons = -0.3/sqrt((self.x - HoneyBee.hiveX)**2 + (self.y - HoneyBee.hiveY)**2)
                self.x += cons * scale * (self.x - HoneyBee.hiveX)
                self.y += cons * scale * (self.y - HoneyBee.hiveY)
        elif self.mode == -2:
            self.wagdance_t += 1
            if self.wagdance_t >= self.timeWagDance:
                self.wagdance_t = 0
                if self.persistence == 0:
                    self.leaveHive(mode=0)
                else:
                    self.leaveHive(mode=-3)
                self.Hive.broadcastedPositions.pop(self.BeeId)
        if abs(self.x - HoneyBee.hiveX) > HoneyBee.hiveX or abs(self.y - HoneyBee.hiveY) > HoneyBee.hiveX:
            self.x = HoneyBee.hiveX
            self.y = HoneyBee.hiveY
            if self.bclass == 0:
                self.mode = 0
            else:
                self.mode = 1
        if self.mode in (0, -3):
            self.steps_without_resource += 1
        return

    def new_drift_vector(self):
        if self.target is not None:
            base = np.array(self.target) - np.array([self.x, self.y])
            if la.norm(base) == 0:
                base = np.array([random.random()-0.5, random.random()-0.5])
            else:
                base = base / la.norm(base)
            noise = np.array([random.random()-0.5, random.random()-0.5])
            self.v_drift = 0.95 * base + 0.05 * noise
            self.v_drift = self.v_drift / la.norm(self.v_drift)
            self.theta = atan2(self.v_drift[1], self.v_drift[0])
        else:
            self.v_drift = np.array([random.random()-0.5, random.random()-0.5])
            self.v_drift = self.v_drift / la.norm(self.v_drift)
            self.theta = atan2(self.v_drift[1], self.v_drift[0])
        return

    def exploiterReturned(self):
        if self.returnCount == self.persistence:
            self.mode = 1
            self.update = self.Recruitment
            self.returnCount = 0
        elif self.returnCount == 0:
            if np.random.rand() < 0.1:
                self.mode = -2
                self.broadcastSpot()
                self.returnCount += 1
            else:
                self.returnCount += 1
                self.leaveHive(mode=-3)
        else:
            self.returnCount += 1
            self.leaveHive(mode=-3)
        self.x = HoneyBee.hiveX
        self.y = HoneyBee.hiveY
        self.updatePos = self.exploiterWalk
        self.Hive.addFood()
        self.nectar = 0
        self.steps_without_resource = 0
        return

    def explorerReturned(self):
        if self.returnCount == self.persistence:
            self.leaveHive(mode=0)
        elif self.returnCount == 0:
            self.mode = -2
            self.broadcastSpot()
            self.returnCount += 1
        else:
            self.returnCount += 1
            self.leaveHive(mode=-3)
        self.x = HoneyBee.hiveX
        self.y = HoneyBee.hiveY
        self.Hive.addFood()
        self.nectar = 0
        self.steps_without_resource = 0
        return

    def leaveHive(self, mode=0):
        self.mode = mode
        self.update = self.move
        if self.mode == 0:
            self.spot = []
            self.returnCount = 0
            self.v = self.v_explore
            self.tsigma = self.tsigma_explore
            self.updatePos = self.DriftRandomWalk
            self.v_drift = self.new_drift_vector()
            self.recruitedSpot = []
        elif mode == -3:
            self.v = self.v_exploit
            self.tsigma = self.tsigma_exploit
            self.updatePos = self.exploiterWalk
            U = self.spot
            self.recruitedSpot = np.array(U)
            hive_pos = np.array([HoneyBee.hiveX, HoneyBee.hiveY])
            u = np.array(U) - hive_pos
            norm_u = la.norm(u)
            if norm_u < 5.0:
                fallback = np.array(self.target) - hive_pos
                self.v_drift = fallback / la.norm(fallback)
            else:
                self.v_drift = u / norm_u
            self.theta = atan2(self.v_drift[1], self.v_drift[0])
        return

    def broadcastSpot(self):
        self.Hive.broadcastedPositions[self.BeeId] = self.spot
        return

    def Recruitment(self):
        Pos = np.array(list(self.Hive.broadcastedPositions.values()))
        if Pos.shape[0] > 0 and random.random() < self.Krecruitment / float(self.Hive.Nexploiters - self.Hive.Nrecruiteds):
            U = Pos[np.random.choice(np.arange(Pos.shape[0]), 1)[0]]
            self.mode = 0
            self.update = self.move
            self.recruitedSpot = np.array(U)
            self.spot = self.recruitedSpot
            hive_pos = np.array([HoneyBee.hiveX, HoneyBee.hiveY])
            u = np.array(U) - hive_pos
            norm_u = la.norm(u)
            if norm_u < 5.0:
                fallback = np.array(self.target) - hive_pos
                self.v_drift = fallback / la.norm(fallback)
            else:
                self.v_drift = u / norm_u
            self.theta = atan2(self.v_drift[1], self.v_drift[0])
        return

    def energyUpdate(self, dx):
        self.energy += (self.dE_a + self.dE_b * dx**3)
        return

    def stayInHive(self):
        return

    def StraightLine(self):
        dx = 1.0 + int(3 * random.random()) - 1
        dy = int(3 * random.random()) - 1
        self.x += dx
        self.y += dy
        self.energyUpdate(sqrt(dx**2 + dy**2))
        return

    def DriftRandomWalk(self):
        theta = self.theta + self.tsigma * (random.random() - 0.5)
        dx = self.v * cos(theta)
        dy = self.v * sin(theta)
        self.x += dx
        self.y += dy
        self.energyUpdate(sqrt(dx**2 + dy**2))
        return

    def exploiterWalk(self):
        theta = self.theta + self.tsigma * (random.random() - 0.5)
        dx = self.v * cos(theta)
        dy = self.v * sin(theta)
        self.x += dx
        self.y += dy
        self.energyUpdate(sqrt(dx**2 + dy**2))
        d = la.norm(self.recruitedSpot - np.array([HoneyBee.hiveX, HoneyBee.hiveY])) - la.norm(np.array([int(self.x), int(self.y)]) - np.array([HoneyBee.hiveX, HoneyBee.hiveY]))
        if d < 0:
            self.updatePos = self.RandomWalkUpdate
        return

    def RandomWalkUpdate(self):
        dx = 3 * (random.random() - 0.5)
        dy = 3 * (random.random() - 0.5)
        self.x += dx
        self.y += dy
        self.energyUpdate(sqrt(dx**2 + dy**2))
        return
