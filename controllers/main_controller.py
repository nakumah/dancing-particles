import os.path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from core.audio_analyzer import AudioAnalyzer
from core.audio_analyzer_thread import AudioAnalyzerThread
from views.main_window import VMainWindow


class MainController:

    def __init__(self, view: VMainWindow, app: QApplication):
        self.view = view
        self.app = app

        self.audioAnalyzer: AudioAnalyzer | None = None
        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.__handleTimeElapsed)

        self.view.progressBar.hide()
        self.view.progressBar.setRange(0, 0) # indeterminate

        self.initGL()
        self.setView(view)
        self.__configure()

    # region configure

    def __configure(self):
        self.view.loadBtn.clicked.connect(self.__handleLoadClick)
        self.view.stopBtn.clicked.connect(self.__handleStopClicked)
        self.view.startBtn.clicked.connect(self.__handleStartClicked)

    # endregion

    # region event handlers
    def __handleTimeElapsed(self):
        if not self.audioAnalyzer:
            return

        energy, color = self.audioAnalyzer.step()
        for p in self.view.glWidget.particles:
            p.update(energy)

        self.updateScene()


    def __handleLoadClick(self):
        path, _ = QFileDialog.getOpenFileName(self.view, "Select MP3", "", "Audio Files (*.mp3 *.wav)")
        if not os.path.isfile(path):
            return

        self.loadFile(path)

    def __handleStopClicked(self):
        self.timer.stop()

    def __handleStartClicked(self):
        self.timer.start(16)

    # endregion

    # region workers

    def initGL(self):
        self.view.glWidget.createParticles(2000)
        # self.updateScene()

    def updateScene(self):
        # redraw the particles
        return
        self.view.glWidget.update()

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

