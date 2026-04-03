import numpy as np
from OpenGL.GL import *

class Particle:
    def __init__(self, pos = None):
        self.vel = np.zeros(3)
        self.alpha = 1.0
        self.color = (1.0, 1.0, 1.0, 1.0)

        # we assign a default position to the particle
        self.__defaultPosition = pos
        self.pos = pos
        if pos is None:
            self.__defaultPosition = np.random.randn(3)
            self.pos = self.__defaultPosition

    def update(self, energy: float, color = (1.0, 1.0, 1.0, 1.0)):
        assert isinstance(energy, float), f"Expected float, got {type(energy)} with value {energy}"
        assert len(color) == 4

        noise = np.random.randn(3) * 0.01
        self.vel += noise * energy
        self.pos += self.vel
        self.pos /= np.linalg.norm(self.pos)
        self.color = color

    def update_ii(self, energy: float, color=(1.0, 1.0, 1.0, 1.0)):
        assert isinstance(energy, float)
        assert len(color) == 4

        pos_norm = self.pos / np.linalg.norm(self.pos)

        # --- Generate random tangent direction
        noise = np.random.randn(3)

        # Project onto tangent plane
        noise -= np.dot(noise, pos_norm) * pos_norm

        # Normalize noise
        n = np.linalg.norm(noise)
        if n > 0:
            noise /= n

        # --- Apply force (tangential only)
        self.vel += noise * energy * 0.01

        # --- 🔥 CRITICAL: re-project velocity onto tangent plane
        self.vel -= np.dot(self.vel, pos_norm) * pos_norm

        # --- Optional damping (prevents explosion)
        self.vel *= 0.98

        # --- Integrate position with angular velocity
        # self.pos += self.vel
        omega = noise * energy * 0.01
        self.pos += np.cross(omega, self.pos)

        # --- Re-project position to sphere
        self.pos /= np.linalg.norm(self.pos)

        self.color = color

    def reset(self):
        self.pos = self.__defaultPosition
    # region opengl

    def draw(self):
        glColor4f(*self.color)
        glVertex3f(*self.pos)

    # endregion