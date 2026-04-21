import numpy as np
from OpenGL.GL import *

from models.particles.particle import Particle


class SphereParticle(Particle):


    def __init__(self, position: np.ndarray):
        super().__init__(position)

        ELEMENTARY_CHARGE = 1.602e-19

        self.radius: float = 1e-11 # m
        self.mass = 5.6e-10 # kg
        self.charge: float = 2e5 * ELEMENTARY_CHARGE

    def draw(self):
        glColor4f(*self.color)
        glVertex3f(*self.position)

    def distanceBetween(self, p: "SphereParticle") -> float:
        radiusOffset = p.radius + self.radius
        return float(np.linalg.norm(self.position - p.position)) - radiusOffset