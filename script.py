import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import os
import time
import threading
import subprocess
import configparser

"""
Brightness controller class

Parameters:
    poll_interval: polling (seconds)

Functions:
    ambient_brightness_backlight_set: map ambient sensor onto brightness
    set_brightness: set brightness
    get_brightness: get brightness
    
Objects:
    AutoBrightnessPolling: automatically poll at polling rate to change brightness automatically
"""
class BrightnessController:

    def __init__(self):
        base_backlight_path = "/sys/class/backlight"
        base_ambient_sensor_path = "/sys/bus/iio/devices"

        try:
            # Find first usable backlight device
            device = next((d for d in os.listdir(base_backlight_path) if "intel" in d or "acpi" in d or "amdgpu_bl"), None)
            if not device:
                raise RuntimeError("No backlight device found")

            self.brightness_path = os.path.join(base_backlight_path, device, "brightness")
            print(f"Found backlight device: {self.brightness_path}")
            max_path = os.path.join(base_backlight_path, device, "max_brightness")

            with open(max_path, "r") as f:
                self.max_brightness = int(f.read().strip())
                print(f"Max device brightness: {self.max_brightness}")

        except Exception as e:
            print(f"Brightness device error: {e}")

        try:
            device = next((d for d in os.listdir(base_ambient_sensor_path) if "iio" in d),None)
            if not device:
                raise RuntimeError("No ambient sensor device found")

            self.ambient_sensor_path = os.path.join(base_ambient_sensor_path, device, "in_illuminance_raw")

        except Exception as e:
            print(f"Ambient sensor device error: {e}")

    def ambient_brightness_backlight_set(self):
        try:

            with open(self.ambient_sensor_path, "r") as f:
                ambient_brightness = int(f.read().strip())

            current = int(self.get_brightness())
            target = int(ambient_brightness * 200)
            step_count = 10

            # Prevent tiny loops or no movement
            if current == target:
                return

            step = (target - current) / step_count

            print(f"Target brightness: {target}")

            for i in range(1, step_count + 1):
                level = int(current + step * i)
                level = max(0, min(level, self.max_brightness))  # Clamp
                print(f"Setting brightness to: {level}")
                self.set_brightness(level)
                time.sleep(0.05)

        except Exception as e:
            print(f"Ambient brightness backlight set error: {e}")

    def set_brightness(self,level):
        try:
            level = max(0, min(level, self.max_brightness))  # Clamp
            with open(self.brightness_path, "w") as f:
                f.write(str(level))

            print(f"Brightness set to {level}/{self.max_brightness}")

        except Exception as e:
            print(f"Error setting brightness: {e}")

    def get_brightness(self):
        try:
            with open(self.brightness_path, "r") as f:
                return int(f.read().strip())

        except Exception as e:
            print(f"Error getting brightness: {e}")

    class AutoBrightnessPoller(threading.Thread):
        def __init__(self, controller, poll_interval):
            super().__init__()
            self.poll_interval = poll_interval
            self.controller = controller
            self.running = True
            self.daemon = True

        def stop(self):
            print(f"Stopping auto-brightness")
            self.running = False

        def run(self):
            print(f"Auto brightness running")
            try:
                while self.running:
                    self.controller.ambient_brightness_backlight_set()
                    time.sleep(self.poll_interval)
            except Exception as e:
                print(f"Auto brightness error: {e}")

class PowerModeController:
    def __init__(self,high_power,low_power):
        self.high_power = high_power
        self.low_power = low_power

    def set_tuned_profile_to_high(self):
        try:
            subprocess.run(['tuned-adm', 'profile', self.high_power], check=True)
            print(f"Tuned profile set to '{self.high_power}'")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set tuned profile: {e}")

    def set_tuned_profile_to_low(self):
        try:
            subprocess.run(['tuned-adm', 'profile', self.low_power], check=True)
            print(f"Tuned profile set to '{self.low_power}'")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set tuned profile: {e}")

"""
dbus power state change handler on upower
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
            5: "Pending charge",
            6: "Pending discharge"
        }
        print(f"Battery State Changed: {state_map.get(state, 'Unknown')}")

        if state == 1 or state == 4:
            ac()
        elif state == 2 or state == 3:
            bat()


"""
dbus listener for upower property changes
"""
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

def start():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    battery_path = None

    # Find the battery device
    upower = bus.get_object("org.freedesktop.UPower", "/org/freedesktop/UPower")
    upower_iface = dbus.Interface(upower, "org.freedesktop.UPower")
    devices = upower_iface.EnumerateDevices()

    for path in devices:
        dev = bus.get_object("org.freedesktop.UPower", path)
        props = dbus.Interface(dev, "org.freedesktop.DBus.Properties")
        device_type = props.Get("org.freedesktop.UPower.Device", "Type")
        if device_type == 2:  # 2 = Battery
            battery_path = path
            break

    if not battery_path:
        print("Battery device not found.")
        return

    # Get battery state
    battery = bus.get_object("org.freedesktop.UPower", battery_path)
    battery_props = dbus.Interface(battery, "org.freedesktop.DBus.Properties")
    state = battery_props.Get("org.freedesktop.UPower.Device", "State")

    print(f"Initial battery state: {state}")

    if state in (1, 4):  # Charging or Fully charged
        ac()
    elif state in (2, 3):  # Discharging or Empty
        bat()

def bat():
    global controller, poller, powermode_controller, polling_interval

    if not poller or not poller.is_alive():
        poller = controller.AutoBrightnessPoller(controller, polling_interval)
        poller.start()
    powermode_controller.set_tuned_profile_to_low()

def ac():
    global controller, poller, powermode_controller
    if poller and poller.is_alive():
        poller.stop()
        poller.join()  # Wait for thread to finish
    controller.set_brightness(controller.max_brightness)
    powermode_controller.set_tuned_profile_to_high()

if __name__ == "__main__":
    polling_interval = float(os.environ.get("POLL_INTERVAL", 1))
    high_power_profile = os.environ.get("HIGH_POWER_PROFILE", "throughput-performance")
    low_power_profile = os.environ.get("LOW_POWER_PROFILE", "powersave")

    controller = BrightnessController()
    poller = controller.AutoBrightnessPoller(controller, polling_interval)
    powermode_controller = PowerModeController(high_power_profile,low_power_profile)

    start()
    setup_listener()


