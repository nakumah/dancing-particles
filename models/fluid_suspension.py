
class FluidSuspension:

    def __init__(self):
        self.__volume = 1.0
        self.__density = 1.0
        self.__velocity = 1.0
        self.__speedOfSound = 343.0

    # region setters
    def setSpeedOfSound(self, speedOfSound: float):
        self.__speedOfSound = speedOfSound

    def setVelocity(self, velocity: float):
        self.__velocity = velocity

    def setVolume(self, volume: float):
        self.__volume = volume

    def setDensity(self, density: float):
        self.__density = density

    # endregion

    # region getters
    def speedOfSound(self):
        return self.__speedOfSound

    def density(self):
        return self.__density

    def volume(self):
        return self.__volume

    def velocity(self):
        return self.__velocity

    # endregion
