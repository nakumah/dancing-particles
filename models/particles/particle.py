
import numpy as np


class Particle:
    def __init__(self, position: np.ndarray = np.zeros(3)):
        self.position: np.ndarray = position
        self.velocity: np.ndarray =  np.array([0.0, 0.0, 0.0]) # m/s
        self.acceleration: np.ndarray =  np.array([0.0, 0.0, 0.0]) # m/s^2
        self.mass: float = 0.0 # kg
        self.color: np.ndarray = np.array([1.0, 1.0, 1.0, 1.0]) #rgba
        self.charge: float = 1.0

    def area(self) -> float:
        raise NotImplementedError

    def volume(self) -> float:
        raise NotImplementedError

    def draw(self):
        raise NotImplementedError("subclass and then implement draw")

    def distanceBetween(self, p: "Particle") -> float:
        return float(np.linalg.norm(self.position - p.position))