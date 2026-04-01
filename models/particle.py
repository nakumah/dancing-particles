import numpy as np
from OpenGL.GL import *

class Particle:
    def __init__(self):
        self.pos = np.random.randn(3)
        self.pos /= np.linalg.norm(self.pos)
        self.vel = np.zeros(3)
        self.alpha = 1.0

    def update(self, energy, color=1.0):
        noise = np.random.randn(3) * 0.01
        self.vel += noise * energy
        self.pos += self.vel
        self.pos /= np.linalg.norm(self.pos)
        self.alpha = color

    # region opengl

    def draw(self):
        glColor4f(1.0, 1.0, 1.0, self.alpha)  # white
        glVertex3f(*self.pos)

    # endregion