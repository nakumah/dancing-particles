from PySide6.QtCore import QThread, Signal

from core.audio_analyzer import AudioAnalyzer


class AudioAnalyzerThread(QThread):

    failed = Signal(object)
    def __init__(self, filePath: str, parent=None):
        super().__init__(parent=parent)

        self.filePath = filePath
        self.analyzer = None
        self.error = None

    def run(self):
        try:
            self.analyzer = AudioAnalyzer(self.filePath)

        except Exception as e:
            self.error = e
