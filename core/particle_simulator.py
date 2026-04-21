import numpy as np
import pyqtgraph.opengl as gl

from models.fluid_suspension import FluidSuspension
from models.particles.particle import Particle
from models.particles.sphere_particle import SphereParticle


GRAVITATIONAL_ACCELERATION = 9.81
MAX_HOOKES_DISTANCE = 1e-9 # m
MIN_HOOKES_DISTANCE = 1e-6 # m
COULOMBS_CONSTANT = 8.99e10
GRAVITATIONAL_CONSTANT = 6.67e-11


class SpatialGrid:
    def __init__(self, cellSize: float = 0.1, lowerBound: int = -1, upperBound: int = 1):
        self.cellSize = cellSize
        self.lowerBound = lowerBound
        self.upperBound = upperBound

        cellCount = int((upperBound - lowerBound) / cellSize)
        coords = np.linspace(lowerBound, upperBound, cellCount)
        X, Y, Z = np.meshgrid(coords, coords, coords, indexing="ij")
        self.vertices = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)

    def boundingCube(self, point: np.ndarray) -> np.ndarray:
        """ returns the bounding rectangle for a point """

        def extractBoundsAtAxis(value: float, axis: int) -> tuple[float, float]:
            coords = self.vertices[:, axis]

            lowerCandidates = coords[coords <= value]
            upperCandidates = coords[coords >= value]

            if len(lowerCandidates) == 0 or len(upperCandidates) == 0:
                raise ValueError(f"Point is outside the vertex bounds {point}, with value {value} at axis {axis}", )

            lb = np.max(lowerCandidates)  # closest below
            ub = np.min(upperCandidates)  # closest above

            return float(lb), float(ub)

        xBoundsArr = np.array(extractBoundsAtAxis(float(point[0]), 0))
        yBoundsArr = np.array(extractBoundsAtAxis(float(point[1]), 1))
        zBoundsArr = np.array(extractBoundsAtAxis(float(point[2]), 2))

        X, Y, Z = np.meshgrid(xBoundsArr, yBoundsArr, zBoundsArr, indexing="ij")
        boundsVertices = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)
        return boundsVertices

    @staticmethod
    def constructCubeAroundCenter(center: np.ndarray, sideLength: float) -> np.ndarray:
        h = sideLength / 2.0

        # All combinations of ±h
        offsets = np.array([
            [-h, -h, -h],
            [-h, -h, h],
            [-h, h, -h],
            [-h, h, h],
            [h, -h, -h],
            [h, -h, h],
            [h, h, -h],
            [h, h, h],
        ])

        return center + offsets

    @staticmethod
    def cubeCenter(cube: np.ndarray) -> np.ndarray:
        return np.sum(cube, axis=0) / 8

    @staticmethod
    def cubeContainsPoint(point: np.ndarray, cube: np.ndarray) -> bool:
        point = np.asarray(point)

        mins = cube.min(axis=0)
        maxs = cube.max(axis=0)

        return np.all((point >= mins) & (point <= maxs))

class ParticleSimulator:

    def __init__(self, ):
        self.__particles: list[SphereParticle] = []
        self.__fluidSuspension = FluidSuspension()
        self.__gridSize = 20
        self.__time: float = 0.0
        self.__spatialGrid = SpatialGrid()

    # region getters
    def particles(self):
        return self.__particles

    # endregion

    # region setters

    def setParticles(self, particles):
        self.__particles = particles

    # endregion

    # region workers

    def spawnParticles(self, ) -> list[SphereParticle]:
        """ spawn particles in at positions."""

        # keep it simple and spawn the particles in a sphere around the center
        circleMesh = gl.MeshData.sphere(rows=10, cols=10, radius=0.5)
        vertices: np.ndarray = circleMesh.vertexes()
        particles = [SphereParticle(position=vertices[i, :]) for i in range(vertices.shape[0])]

        self.__particles = particles
        return particles

    @staticmethod
    def computeParticleDisplacement(initialVelocity: np.ndarray,acceleration: np.ndarray, time: float,) -> np.ndarray:
        """ s = ut + 0.5 * a * t^2 """
        return (initialVelocity * time) + 0.5 * acceleration * (time ** 2)

    @staticmethod
    def computeParticleVelocity(initialVelocity: np.ndarray, acceleration: np.ndarray, displacement: np.ndarray) -> np.ndarray:
        """ v = sqr(u ^ 2 + 2 * a * s) """

        return np.sqrt(np.pow(initialVelocity, 2) + 2 * acceleration * displacement)

    @staticmethod
    def computeGravity(mass: float) -> np.ndarray:
        return np.array([0, 0, -GRAVITATIONAL_ACCELERATION]) * mass

    def estimateStiffnessFromChargeAndGravity(self, p1: Particle, p2: Particle) -> float:
        """
        perform a force balance between attraction and repulsion force from gravitational attraction and charge repulsion.
        """

        r = p1.distanceBetween(p2)
        q = (2 * COULOMBS_CONSTANT * p1.charge * p2.charge) / r**3
        g = (2 * GRAVITATIONAL_CONSTANT * p1.mass * p2.mass) / r**3

        return q - g

    def computeHookesForce(self, stiffness, naturalLength, p1: Particle, p2: Particle) -> np.ndarray:
        # F = k * (current_dist - natural_length)
        distance = p2.distanceBetween(p1)
        f = stiffness * (distance - naturalLength)
        forceXYZ = ((p2.position - p1.position) * distance) * f
        return forceXYZ


    def computeHookesForcesFromNeighbours(self, particle: Particle, neighbours: list[Particle]) -> np.ndarray:

        forces = np.zeros(3, dtype=float)

        for p in neighbours:
            # stiffness = self.estimateStiffnessFromChargeAndGravity(particle, p)
            stiffness = 10
            naturalLength = MIN_HOOKES_DISTANCE
            hookeForce = self.computeHookesForce(stiffness, naturalLength, particle, p)
            forces += hookeForce

        return forces

    def findParticleNeighbours(self, particle: Particle) -> list[Particle]:

        # get bounding cell for that particle
        particleCell = self.__spatialGrid.boundingCube(particle.position)
        assert self.__spatialGrid.cubeContainsPoint(particle.position, particleCell), "Point not inside cube. this should not happen"

        # because the particle could lie on the boundary of the cell.,
        # construct a larger working area
        smallCellCenter = self.__spatialGrid.cubeCenter(particleCell)
        largerCell = self.__spatialGrid.boundingCube(smallCellCenter)

        # now, we iterate through our particles and find those that exist in large cell
        neighbours: list[Particle] = []
        for p in self.__particles:
            isInCell = self.__spatialGrid.cubeContainsPoint(p.position, largerCell)
            isWithinRange = particle.distanceBetween(p)
            if isInCell and isWithinRange:
                neighbours.append(p)

        return neighbours

    def advance(self, dt: float):
        """ Resolves all particle forces and updates the positions """
        self.__time += dt

        for i, particle in enumerate(self.__particles):
            neighbors: list[Particle] = self.findParticleNeighbours(particle)
            hookes_forces: np.ndarray = 10 * self.computeHookesForcesFromNeighbours(particle, neighbors)
            gravityForce: np.ndarray = self.computeGravity(particle.mass)
            forces = hookes_forces + gravityForce

            acceleration: np.ndarray = particle.mass * (forces)
            displacement: np.ndarray = self.computeParticleDisplacement(initialVelocity=particle.velocity, acceleration=acceleration, time=self.__time)
            finalVelocity: np.ndarray = self.computeParticleVelocity(initialVelocity=particle.velocity, acceleration=acceleration, displacement=displacement, )

            # update the particle variables
            particle.position += displacement
            particle.velocity = finalVelocity
            particle.acceleration = acceleration

            if i == 0:
                print(forces)

        print("Advance: t = ", self.__time)

    # endregion
