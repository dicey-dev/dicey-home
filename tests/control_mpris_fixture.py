"""Silent, test-only MPRIS player. It produces no audio and controls no real app."""
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

PLAYER = "org.mpris.MediaPlayer2.Player"
ROOT = "org.mpris.MediaPlayer2"
PROPS = "org.freedesktop.DBus.Properties"
TEST = "org.dicey.Home.Test"
DBusGMainLoop(set_as_default=True)


class Fixture(dbus.service.Object):
    def __init__(self, bus):
        self.name = dbus.service.BusName("org.mpris.MediaPlayer2.dicey_control_test", bus, do_not_queue=True)
        super().__init__(bus, "/org/mpris/MediaPlayer2")
        self.playing = False
        self.track = 1
        self.position = 0
        self.calls = {"playPause": 0, "next": 0, "previous": 0, "seek": 0}

    def properties(self, interface):
        if interface == ROOT:
            return {"Identity": "Dicey Home test player", "DesktopEntry": "dicey_control_test", "CanRaise": False,
                    "CanQuit": False, "HasTrackList": False, "SupportedUriSchemes": dbus.Array([], signature="s"),
                    "SupportedMimeTypes": dbus.Array([], signature="s")}
        return {"PlaybackStatus": "Playing" if self.playing else "Paused", "LoopStatus": "None", "Rate": 1.0,
                "Shuffle": False, "Volume": 1.0, "Position": dbus.Int64(self.position), "MinimumRate": 1.0,
                "MaximumRate": 1.0, "CanGoNext": True, "CanGoPrevious": True, "CanPlay": True, "CanPause": True,
                "CanSeek": True, "CanControl": True,
                "Metadata": dbus.Dictionary({"mpris:trackid": dbus.ObjectPath("/track/one"), "mpris:length": dbus.Int64(180000000),
                                             "xesam:title": f"Dicey Home test track {self.track}",
                                             "xesam:artist": dbus.Array(["Silent fixture"], signature="s")}, signature="sv")}

    @dbus.service.method(PROPS, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.properties(interface)

    @dbus.service.method(PROPS, in_signature="ss", out_signature="v")
    def Get(self, interface, name):
        return self.properties(interface)[name]

    @dbus.service.method(PROPS, in_signature="ssv")
    def Set(self, interface, name, value):
        pass

    @dbus.service.signal(PROPS, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changes, invalidated):
        pass

    @dbus.service.signal(PLAYER, signature="x")
    def Seeked(self, position):
        pass

    @dbus.service.method(PLAYER)
    def PlayPause(self):
        self.calls["playPause"] += 1
        self.playing = not self.playing
        self.PropertiesChanged(PLAYER, {"PlaybackStatus": "Playing" if self.playing else "Paused"}, [])

    @dbus.service.method(PLAYER)
    def Play(self):
        self.playing = True
        self.PropertiesChanged(PLAYER, {"PlaybackStatus": "Playing"}, [])

    @dbus.service.method(PLAYER)
    def Pause(self):
        self.playing = False
        self.PropertiesChanged(PLAYER, {"PlaybackStatus": "Paused"}, [])

    @dbus.service.method(PLAYER)
    def Next(self):
        self.calls["next"] += 1
        self.track += 1
        self.PropertiesChanged(PLAYER, {"Metadata": self.properties(PLAYER)["Metadata"]}, [])

    @dbus.service.method(PLAYER)
    def Previous(self):
        self.calls["previous"] += 1
        self.track = max(1, self.track - 1)
        self.PropertiesChanged(PLAYER, {"Metadata": self.properties(PLAYER)["Metadata"]}, [])

    @dbus.service.method(PLAYER, in_signature="ox")
    def SetPosition(self, track, position):
        self.calls["seek"] += 1
        self.position = int(position)
        self.Seeked(self.position)

    @dbus.service.method(TEST, out_signature="a{sv}")
    def Counts(self):
        return self.calls


fixture = Fixture(dbus.SessionBus())
print("ready", flush=True)
GLib.MainLoop().run()
