from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import (GLUT_BITMAP_HELVETICA_18)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QVector3D, QMatrix4x4, QVector2D
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from core.app_colors import appColors
from models.camera import Camera
from models.particle import Particle


class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.__frameTimer = QTimer()
        self.__frameTimer.setSingleShot(False)
        self.__frameTimer.setInterval(16)  # ~60 FPS
        self.__frameTimer.timeout.connect(self.__handleFrameTimer)
        self.__frameTimer.start()

        self.__backgroundColor = QColor(appColors.dark_rbg)

        self.__camera = Camera(self)
        self.__camera.setLocation(QVector3D(0, 0, 10))  # or 10
        self.__camera.setFocusPoint(QVector3D(0, 0, 0))

        self.__mousePos: QVector2D = QVector2D(0, 0)
        self.__particles: list[Particle] = []

    # region openGL

    def initializeGL(self, /):

        glClearColor(self.__backgroundColor.redF(), self.__backgroundColor.greenF(), self.__backgroundColor.blueF(), 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPointSize(3)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(
            self.__camera.location().x(), self.__camera.location().y(), self.__camera.location().z(),
            self.__camera.focusPoint().x(), self.__camera.focusPoint().y(), self.__camera.focusPoint().z(),
            self.__camera.up().x(), self.__camera.up().y(), self.__camera.up().z(),
        )

        glBegin(GL_POINTS)
        for p in self.__particles:
            p.draw()
        glEnd()

    def resizeGL(self, w, h, /):
        h = max(1, h)

        glViewport(0, 0, w, h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        aspect = w / h
        gluPerspective(45.0, aspect, 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)

    # endregion

    # region camera interactions

    def mousePressEvent(self, event):
        self.__mousePos = QVector2D(event.localPos())

    def mouseReleaseEvent(self, event, /):
        self.__mousePos = QVector2D(event.localPos())

    def mouseDoubleClickEvent(self, event, /):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.__resetCamera()
        return super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        # if not self.__mousePos:
        #     return

        pos = QVector2D(event.localPos())
        diff = pos - self.__mousePos
        focusVector = self.__camera.location() - self.__camera.focusPoint()
        up = self.__camera.up().normalized()
        right = QVector3D.crossProduct(self.__camera.up(), focusVector)

        if event.buttons() == Qt.MouseButton.LeftButton:
            matrix = QMatrix4x4()
            matrix.rotate(-diff.x(), up)
            matrix.rotate(-diff.y(), right)

            newFocusVector = matrix.map(focusVector)
            newCameraPos = newFocusVector + self.__camera.focusPoint()

            self.__camera.setLocation(newCameraPos)
            self.__camera.setUp(matrix.mapVector(up).normalized())

            dt = QVector3D.dotProduct(self.__camera.up(), newFocusVector)
            v = QVector3D(self.__camera.up())
            v.setX(v.x() * dt)
            v.setY(v.y() * dt)
            v.setZ(v.z() * dt)
            self.__camera.setUp(self.__camera.up() - (v * self.__camera.up()).normalized())

        if event.buttons() == Qt.MouseButton.RightButton:
            pdr = QVector3D(right)
            pdr.setX(-diff.x() / self.width() * right.x())
            pdr.setY(-diff.x() / self.width() * right.y())
            pdr.setZ(-diff.x() / self.width() * right.z())

            pdu = QVector3D(up)
            pdu.setX(diff.y() / self.height() * up.x())
            pdu.setY(diff.y() / self.height() * up.y())
            pdu.setZ(diff.y() / self.height() * up.z())
            panDelta = pdr + pdu

            self.__camera.setLocation(self.__camera.location() + panDelta)
            self.__camera.setFocusPoint(self.__camera.focusPoint() + panDelta)

        self.__mousePos = QVector2D(event.localPos())

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        focusVector = self.__camera.location() - self.__camera.focusPoint()
        mul = -delta / 1000.0

        loc = QVector3D(self.__camera.location())
        loc.setX(mul * focusVector.x() + loc.x())
        loc.setY(mul * focusVector.y() + loc.y())
        loc.setZ(mul * focusVector.z() + loc.z())
        self.__camera.setLocation(loc)

    # endregion

    # region workers

    def __resetCamera(self):
        self.__camera.setFocusPoint(QVector3D(0, 0, 0))

    # endregion

    # region event handlers
    def __handleFrameTimer(self):
        self.update()

    # endregion

    # region setters

    def setParticles(self, particles: list[Particle]):
        self.__particles = particles

    # endregion

    # region getters

    def particles(self) -> list[Particle]:
        return self.__particles
    # endregion
