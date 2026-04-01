import sys
import numpy as np
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QTimer

from OpenGL.GL import *


# ---------------- PARTICLES ----------------


# ---------------- OPENGL WIDGET ----------------
class GLWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.particles = [Particle() for _ in range(500)]
        self.audio = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_scene)
        self.timer.start(16)

    def load_audio(self, path):
        self.audio = AudioAnalyzer(path)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glPointSize(3)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glBegin(GL_POINTS)
        for p in self.particles:
            glVertex3f(*p.pos)
        glEnd()

    def update_scene(self):
        if self.audio:
            energy, color = self.audio.step()
            for p in self.particles:
                p.update(energy)
        self.update()

# ---------------- UI ----------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.gl = GLWidget()
        btn = QPushButton("Load MP3")
        btn.clicked.connect(self.load_file)

        layout = QVBoxLayout()
        layout.addWidget(self.gl)
        layout.addWidget(btn)
        self.setLayout(layout)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select MP3", "", "Audio Files (*.mp3 *.wav)")
        if path:
            self.gl.load_audio(path)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec())
