import dbus
import dbus.mainloop.glib
from gi.repository import GLib

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
    setup_listener()

