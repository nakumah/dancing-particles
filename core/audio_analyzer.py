import numpy as np

import librosa
import hashlib


class AudioAnalyzer:
    def __init__(self, path):
        self.y, self.sr = librosa.load(path)
        self.rms = librosa.feature.rms(y=self.y)[0]
        self.centroid = librosa.feature.spectral_centroid(y=self.y, sr=self.sr)[0]
        self.tempo, self.beats = librosa.beat.beat_track(y=self.y, sr=self.sr)

        # normalize
        self.rms /= np.max(self.rms) + 1e-6
        self.centroid /= np.max(self.centroid) + 1e-6

        # seed
        h = hashlib.sha256(self.y.tobytes()).hexdigest()
        seed = int(h[:8], 16)
        np.random.seed(seed)

        self.frame = 0

    def step(self):
        if self.frame >= len(self.rms):
            self.frame = 0
        r = self.rms[self.frame]
        c = self.centroid[self.frame]
        self.frame += 1
        return float(r), float(c)


