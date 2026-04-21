import os.path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFileDialog

from core.app_colors import appColors
from core.audio_analyzer import AudioAnalyzer
from core.audio_analyzer_thread import AudioAnalyzerThread

from core.particle_simulator import ParticleSimulator
from views.main_window import VMainWindow


class MainController:

    def __init__(self, view: VMainWindow, app: QApplication):
        self.view = view
        self.app = app

        self.audioAnalyzer: AudioAnalyzer | None = None
        self.particleSimulator: ParticleSimulator = ParticleSimulator()
        self.timer = QTimer()
        self.timer.setSingleShot(False)

        self.excitationColors = [
            QColor(appColors.tertiary_rbg).getRgbF(),
            QColor(appColors.success_rbg).getRgbF(),
            QColor(appColors.danger_rbg).getRgbF()
        ]

        self.view.progressBar.hide()
        self.view.progressBar.setRange(0, 0)  # indeterminate

        self.initGL()
        self.setView(view)
        self.__configure()

    # region configure

    def __configure(self):
        self.timer.timeout.connect(self.__handleTimeElapsed)
        self.view.loadBtn.clicked.connect(self.__handleLoadClick)
        self.view.stopBtn.clicked.connect(self.__handleStopClicked)
        self.view.startBtn.clicked.connect(self.__handleStartClicked)

    # endregion

    # region event handlers
    def __handleTimeElapsed(self):
        try:
            self.updateParticles()
        except Exception as e:
            self.timer.stop()
            raise Exception("Failed to update particles") from e

    def __handleLoadClick(self):
        path, _ = QFileDialog.getOpenFileName(self.view, "Select MP3", "", "Audio Files (*.mp3 *.wav)")
        if not os.path.isfile(path):
            return

        self.loadFile(path)

    def __handleStopClicked(self):
        self.timer.stop()

    def __handleStartClicked(self):
        self.timer.start(16 * 2) # ~ 60 fps

    # endregion

    # region workers

    def initGL(self):
        self.particleSimulator.spawnParticles()
        self.view.glWidget.setParticles(self.particleSimulator.particles())

    def updateParticles(self):
        # advance forward in time
        timeStep = 1/60
        self.particleSimulator.advance(timeStep)

        # update the particles in the view
        self.view.glWidget.setParticles(self.particleSimulator.particles())

    def loadFile(self, path: str):
        thread = AudioAnalyzerThread(filePath=path)

        def on_start():
            self.audioAnalyzer = None
            self.view.progressBar.show()

        def on_finished():
            self.view.progressBar.hide()

            if thread.error:
                raise thread.error

            self.audioAnalyzer = thread.analyzer
            thread.deleteLater()

        thread.started.connect(on_start)
        thread.finished.connect(on_finished)

        thread.start()

    # endregion

    # region setters

    def setView(self, view: VMainWindow):
        self.view = view
        self.view.resize(800, 600)

    # endregion
