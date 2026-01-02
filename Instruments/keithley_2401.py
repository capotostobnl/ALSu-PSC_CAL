"""
keithley2401.py

Driver for the Keithley 2401 SourceMeter via RS-232/Serial.
"""

import time
import serial


class Keithley2401:
    """
    Interface for Keithley 2401 SourceMeter.
    """

    def __init__(self, port: str = '/dev/ttyUSB2', baudrate: int = 9600,
                 timeout: float = 3.0):
        """
        Establishes the serial connection to the Keithley 2401.

        Args:
            port: The serial port path (e.g., '/dev/ttyUSB2').
            baudrate: Communication speed (default 9600 for older K2400s).
            timeout: Serial timeout in seconds.
        """
        self.port = port
        self.ser = None

        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            # Give the serial connection a moment to stabilize
            time.sleep(0.1)
        except serial.SerialException as e:
            print(f"Failed to open Keithley serial port {port}: {e}")
            raise

    def _write(self, command: str):
        """
        Helper to encode and write a command string.
        Appends Carriage Return (\r) as expected by Keithley SCPI.
        """
        if self.ser:
            # Keithley usually expects \r (CR) as the terminator
            full_cmd = f"{command}\r".encode('utf-8')
            self.ser.write(full_cmd)

    def set_current(self, current_amps: float):
        """
        Configures the source meter to output a specific current.

        Sets the mode to Fixed Current, sets the range to 100mA (0.1A),
        and applies the amplitude.

        Args:
            current_amps: The target current in Amps.
        """
        try:
            # print(f"Keithley: Setting current to {current_amps} A")

            # Set Source Mode to Fixed Current
            self._write("SOUR:CURR:MODE FIX")

            # Set Range to 100mA (0.1).
            self._write("SOUR:CURR:RANG 0.1")

            # Set the actual current amplitude
            self._write(f"SOUR:CURR:AMPL {current_amps}")

        except Exception as e:
            print(f"Error setting Keithley current: {e}")
            raise

    def output_on(self):
        """Enables the output."""
        self._write("OUTP ON")

    def output_off(self):
        """Disables the output."""
        self._write("OUTP OFF")

    def close(self):
        """Closes the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
