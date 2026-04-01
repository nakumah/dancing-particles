import numpy as np

class Particle:
    def __init__(self):
        self.pos = np.random.randn(3)
        self.pos /= np.linalg.norm(self.pos)
        self.vel = np.zeros(3)

    def update(self, energy):
        noise = np.random.randn(3) * 0.01
        self.vel += noise * energy
        self.pos += self.vel
        self.pos /= np.linalg.norm(self.pos)