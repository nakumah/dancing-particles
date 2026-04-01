import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import (GLUT_BITMAP_HELVETICA_18)
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from core.app_colors import appColors
from models.structures import RenderMode


class Node(QObject):
    dead = Signal(str)

    def __init__(self, pid: str):
        super().__init__()

        self.__health = 180  # frames
        self.__maxHealth = 180  # frames
        self.__color = QColor(appColors.danger_rbg)
        self.__position: np.ndarray = np.array([0, 0, 0])

        self.__vertices: np.ndarray = np.array([])
        self.__faces: np.ndarray = np.array([])

        self.__pid = pid
        self.__size = 0.5
        self.__slot: tuple[int, int] = 0, 0

        self.__computeVertices()
        self.__computeFaces()

    # region openGL

    def draw(self, shader: int):
        # uses the shader defined by the landscape

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glUniform1i(glGetUniformLocation(shader, "u_renderMode"), RenderMode.FACES)
        glUniform4f(glGetUniformLocation(shader, "u_faceColor"), *self.glFaceColor())

        # faces
        for face in self.__faces:
            glBegin(GL_QUADS)
            for idx in face:
                glVertex3f(*self.__vertices[idx])
            glEnd()

        # wire frame
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glUniform1i(glGetUniformLocation(shader, "u_renderMode"), RenderMode.EDGES)
        glUniform4f(glGetUniformLocation(shader, "u_edgeColor"), *self.glEdgeColor())
        glLineWidth(2.0)
        for face in self.__faces:
            glBegin(GL_QUADS)
            for idx in face:
                glVertex3f(*self.__vertices[idx])
            glEnd()

    # endregion


    # region setters

    def setPid(self, pid):
        self.__pid = pid

    def setSlot(self, slot: tuple[int, int]):
        self.__slot = slot

    def setSize(self, s: float):
        self.__size = s

    def setCenter(self, pos):
        self.__position = pos
        self.__computeVertices()

    def setHealth(self, health: float):
        self.__health = health
        if not self.isAlive():
            self.dead.emit(self.__pid)

    # endregion

    #region workers

    def __computeFaces(self):
        faces = [
            [0, 1, 2, 3],  # back
            [4, 5, 6, 7],  # front
            [0, 1, 5, 4],  # bottom
            [2, 3, 7, 6],  # top
            [0, 3, 7, 4],  # left
            [1, 2, 6, 5],  # right
        ]
        self.__faces = np.array(faces, dtype=int)

    def __computeVertices(self):
        px, py, pz = self.__position
        d = self.__size / 2

        vertices = [
            [px - d, py - d, pz - d],
            [px + d, py - d, pz - d],
            [px + d, py + d, pz - d],
            [px - d, py + d, pz - d],
            [px - d, py - d, pz + d],
            [px + d, py - d, pz + d],
            [px + d, py + d, pz + d],
            [px - d, py + d, pz + d],
        ]

        self.__vertices = np.array(vertices, dtype=float)

    def hurt(self, damage=1.0):
        self.setHealth(self.__health - damage)

    def heal(self):
        self.setHealth(float(self.__maxHealth))

    def kill(self):
        self.setHealth(0)

    # endregion

    # region getters

    def glFaceColor(self) -> np.ndarray:
        return np.array([
            self.__color.redF(),
            self.__color.greenF(),
            self.__color.blueF(),
            self.__health / self.__maxHealth,
        ])

    def glEdgeColor(self) -> np.ndarray:
        return np.array([
            self.__color.redF(),
            self.__color.greenF(),
            self.__color.blueF(),
            1.0,
        ])

    def pid(self):
        return self.__pid

    def isAlive(self):
        return self.__health > 0

    def slot(self):
        return self.__slot

    def center(self):
        return self.__position

    def health(self):
        return self.__health

    # endregion

    def __str__(self):
        return f"Node(ID={self.__pid}, SIZE={self.__size}, CENTER={self.__position})"
