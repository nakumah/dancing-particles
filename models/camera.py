import numpy as np
from OpenGL.GLUT import (GLUT_BITMAP_HELVETICA_18)
from PySide6.QtCore import QObject
from PySide6.QtGui import QVector3D, QMatrix4x4


class Camera(QObject):
    def __init__(self, parent=None):
        super(Camera, self).__init__(parent)

        self.__fov: float = 60
        self.__aspectRatio: float = 16 / 9
        self.__nearPlane: float = 0.1
        self.__farPlane: float = 100

        self.__focusPoint = QVector3D(0, 0, 0)
        self.__position = QVector3D(0, 0, -100)
        self.__up = QVector3D.crossProduct(QVector3D(-1, 0, 0), self.__position - self.__focusPoint).normalized()

    # region getters
    def focusPoint(self):
        return self.__focusPoint

    def location(self):
        return self.__position

    def up(self):
        return self.__up

    def fov(self):
        return self.__fov

    def aspectRatio(self):
        return self.__aspectRatio

    def nearPlane(self):
        return self.__nearPlane

    def farPlane(self):
        return self.__farPlane

    # endregion

    # region setters

    def setFOV(self, fov: float):
        self.__fov = fov

    def setAspectRatio(self, aspectRatio: float):
        self.__aspectRatio = aspectRatio

    def setNearPlane(self, nearPlane: float):
        self.__nearPlane = nearPlane

    def setFarPlane(self, farPlane: float):
        self.__farPlane = farPlane

    def setLocation(self, vec: QVector3D):
        self.__position = vec

    def setFocusPoint(self, vec: QVector3D):
        self.__focusPoint = vec

    def setUp(self, up: QVector3D):
        self.__up = up

    # endregion

    # region workers

    def loadCamera(self, file: str):
        arr = np.loadtxt(file, delimiter=",", dtype=float)
        self.__focusPoint = QVector3D(float(arr[0, 0]), float(arr[0, 1]), float(arr[0, 2]))
        self.__position = QVector3D(float(arr[1, 0]), float(arr[1, 1]), float(arr[1, 2]))
        self.__up = QVector3D(float(arr[2, 0]), float(arr[2, 1]), float(arr[2, 2]))

    def viewMatrix(self) -> QMatrix4x4:
        matrix = QMatrix4x4()
        matrix.setToIdentity()
        matrix.lookAt(self.__position, self.__focusPoint, self.__up)
        return matrix

    def projectionMatrix(self) -> QMatrix4x4:
        matrix = QMatrix4x4()
        matrix.perspective(self.__fov, self.__aspectRatio, self.__nearPlane, self.__farPlane)
        return matrix

    def identityMatrix(self) -> QMatrix4x4:
        matrix = QMatrix4x4()
        matrix.setToIdentity()
        return matrix

    def MVP_matrix(self):
        view = self.viewMatrix()
        model = self.identityMatrix()
        projection = self.projectionMatrix()

        return projection * view * model

