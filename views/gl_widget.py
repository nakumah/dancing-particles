from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import *

from models.particle import Particle


class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.particles: list[Particle] = []

    def createParticles(self, count: int):
        self.particles = [Particle() for _ in range(count)]

    def initializeGL(self, /):
        glEnable(GL_DEPTH_TEST)
        glPointSize(3)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glBegin(GL_POINTS)
        for p in self.particles:
            glVertex3f(*p.pos)
        glEnd()
