import os
import numpy as np
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

from core.app_colors import appColors
from models.camera import Camera
from .text_renderer import FontRenderer, TextRenderer  # new helper modules

# ───────────────────────────────────────────────
# SHADERS FOR AXIS LINES
# ───────────────────────────────────────────────
VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 position;
uniform mat4 u_mvp;
void main()
{
    gl_Position = u_mvp * vec4(position, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330 core
uniform vec3 u_axisColor;
out vec4 FragColor;
void main()
{
    FragColor = vec4(u_axisColor, 1.0);
}
"""


class Axes(QObject):
    def __init__(self, scale: float = 3.0):
        super().__init__()

        self.__opts: dict[str, ...] = {
            "x": {
                "text": "x",
                "pos": [scale, 0, 0],
                "color": QColor(appColors.danger_rbg)
            },
            "y": {
                "text": "y",
                "pos": [0, scale, 0],
                "color": QColor(appColors.success_rbg)
            },
            "z": {
                "text": "z",
                "pos": [0, 0, scale],
                "color": QColor(appColors.warning_rbg)
            },
        }

        self.shader = None
        self.vao = None
        self.vbo = None

        # text system
        font_path = str(os.path.join(os.getcwd(), "resources", "montserrat.ttf"))
        self.fontRenderer = FontRenderer(font_path, 50)
        self.textRenderer = TextRenderer(self.fontRenderer, self.shader)

    # ───────────────────────────────────────────────
    # GL INIT
    # ───────────────────────────────────────────────
    def initializeGL(self):
        # Compile line shader
        self.shader = compileProgram(
            compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        )

        # Init font + text renderer
        self.textRenderer.setShader(self.shader)
        self.textRenderer.primeGL()
        self.fontRenderer.loadCharacters()

        # Prepare axis geometry (3 lines)
        vertices = np.array([
            0.0, 0.0, 0.0,  self.__opts["x"]["pos"][0], self.__opts["x"]["pos"][1], self.__opts["x"]["pos"][2],
            0.0, 0.0, 0.0,  self.__opts["y"]["pos"][0], self.__opts["y"]["pos"][1], self.__opts["y"]["pos"][2],
            0.0, 0.0, 0.0,  self.__opts["z"]["pos"][0], self.__opts["z"]["pos"][1], self.__opts["z"]["pos"][2],
        ], dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    # ───────────────────────────────────────────────
    # DRAW
    # ───────────────────────────────────────────────
    def draw(self, camera: Camera):
        mvp = camera.MVP_matrix().data()

        # Draw axis lines
        glUseProgram(self.shader)
        u_mvp = glGetUniformLocation(self.shader, "u_mvp")
        glUniformMatrix4fv(u_mvp, 1, GL_FALSE, mvp)

        glBindVertexArray(self.vao)
        glLineWidth(2.0)

        # X axis
        u_axisColor = glGetUniformLocation(self.shader, "u_axisColor")
        glUniform3f(u_axisColor, self.__opts["x"]["color"].redF(),
                    self.__opts["x"]["color"].greenF(),
                    self.__opts["x"]["color"].blueF())
        glDrawArrays(GL_LINES, 0, 2)

        # Y axis
        glUniform3f(u_axisColor, self.__opts["y"]["color"].redF(),
                    self.__opts["y"]["color"].greenF(),
                    self.__opts["y"]["color"].blueF())
        glDrawArrays(GL_LINES, 2, 2)

        # Z axis
        glUniform3f(u_axisColor, self.__opts["z"]["color"].redF(),
                    self.__opts["z"]["color"].greenF(),
                    self.__opts["z"]["color"].blueF())
        glDrawArrays(GL_LINES, 4, 2)

        glBindVertexArray(0)

        # Draw text labels
        for k, axis in self.__opts.items():
            self.textRenderer.renderText(
                axis["text"],
                axis["pos"],
                0.005,  # scale
                (axis["color"].redF(), axis["color"].greenF(), axis["color"].blueF()),
                mvp
            )

    def setScale(self, s: float) -> None:
        self.__opts["x"]["pos"] = [s, 0, 0]
        self.__opts["y"]["pos"] = [0, s, 0]
        self.__opts["z"]["pos"] = [0, 0, s]
