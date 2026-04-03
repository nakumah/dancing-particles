import numpy as np
import pyqtgraph.opengl as gl

from models.particle import Particle


def create_particles_on_sphere(rows = 100, cols=12, radius: float = 1.0,) -> list[Particle]:
    circleMesh = gl.MeshData.sphere(rows=rows, cols=cols, radius=radius)
    vertices: np.ndarray = circleMesh.vertexes()
    particles =  [Particle(vertices[i, :]) for i in range(vertices.shape[0])]
    return particles