import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import os

class BrightnessController:

    def __init__(self):
        self.base_path = "/sys/class/backlight"

        try:
            # Find first usable backlight device
            device = next((d for d in os.listdir(self.base_path) if "intel" in d or "acpi" in d or "amdgpu_bl"), None)
            if not device:
                raise RuntimeError("No backlight device found")

            self.brightness_path = os.path.join(self.base_path, device, "brightness")
            print(f"Found backlight device: {self.brightness_path}")
            max_path = os.path.join(self.base_path, device, "max_brightness")

            with open(max_path, "r") as f:
                self.max_brightness = int(f.read().strip())
                print(f"Max device brightness: {self.max_brightness}")

        except Exception as e:
            print(f"Brightness device error: {e}")

    def set_brightness(self,level):
        try:

            level = max(0, min(level, self.max_brightness))  # Clamp
            with open(self.brightness_path, "w") as f:
                f.write(str(level))

            print(f"Brightness set to {level}/{self.max_brightness}")

        except Exception as e:
            print(f"Error setting brightness: {e}")


"""
dbus listener for fetching the power state of the device
"""

def on_properties_changed(interface, changed_properties, invalidated_properties):

    if 'Online' in changed_properties:
        online = changed_properties['Online']
        print(f"AC Power: {'Online' if online else 'Offline'}")
    if 'State' in changed_properties:
        state = changed_properties['State']
        state_map = {
            0: "Unknown",
            1: "Charging",
            2: "Discharging",
            3: "Empty",
            4: "Fully charged",
        }
        print(f"Battery State Changed: {state_map.get(state, 'Unknown')}")

        global brightness_device_object

        if state == 1 or state == 4:
            brightness_device_object.set_brightness(1000000)



def setup_listener():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Attach to all UPower devices
    upower = bus.get_object("org.freedesktop.UPower", "/org/freedesktop/UPower")
    upower_iface = dbus.Interface(upower, "org.freedesktop.UPower")
    devices = upower_iface.EnumerateDevices()

    for device_path in devices:
        device = bus.get_object("org.freedesktop.UPower", device_path)
        device_iface = dbus.Interface(device, dbus_interface="org.freedesktop.DBus.Properties")
        bus.add_signal_receiver(
            handler_function=on_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            path=device_path,
        )

    print("Listening for power state changes...")
    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    brightness_device_object = BrightnessController()
    setup_listener()


