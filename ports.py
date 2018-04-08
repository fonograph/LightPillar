import serial
from serial.tools import list_ports

print([port.device for port in list_ports.comports()])