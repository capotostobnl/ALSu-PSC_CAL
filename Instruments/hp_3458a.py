"""
hp_3458a.py

Driver for the HP 3458A Digital Multimeter via GPIB-USB controller.
"""

import time
import serial


class HP3458A:
    """
    Interface for HP 3458A DMM using a Prologix GPIB-to-USB controller.
    """

    def __init__(self, port: str = '/dev/ttyUSB0', gpib_addr: int = 24, 
                 baudrate: int = 115200, timeout: float = 30.0):
        """
        Establishes the serial connection to the GPIB controller.

        Args:
            port: The serial port path (e.g., '/dev/ttyUSB0').
            gpib_addr: The GPIB address of the DMM (default 24).
            baudrate: Communication speed for the Prologix controller.
            timeout: Serial timeout in seconds.
        """
        self.port = port
        self.gpib_addr = gpib_addr
        self.timeout = timeout

        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            # Give the serial connection a moment to stabilize
            time.sleep(0.1)
        except serial.SerialException as e:
            print(f"Failed to open DMM serial port {port}: {e}")
            raise

    def _write(self, command: str):
        """Helper to encode and write a command string with a newline."""
        full_cmd = f"{command}\n".encode('utf-8')
        self.ser.write(full_cmd)

    def dmm_init(self):
        """
        Configures the Prologix controller and the DMM for high-precision
        measurement.

        Sequence:
          1. Set GPIB Address.
          2. Disable Auto-Read (Prologix).
          3. Enable Autozero (DMM).
          4. Set Integration time to 30 PLC (DMM).
        """
        print(f"Initializing DMM at GPIB:{self.gpib_addr}...")

        self._write(f"++addr {self.gpib_addr}")
        self._write("++auto 0")

        # --- HP 3458A Instrument Configuration ---
        self._write("AZERO ON")
        self._write("NPLC 30")

        print("DMM Initialization complete.")

    def set_range(self, dmm_range) -> float:
        """Set DMM Range, e.g. 0.1 or 1.0"""
        self._write(f"RANGE {dmm_range}")

    def read_value(self) -> float:
        """
        Triggers a single measurement and returns the float value.
        Matches the logic of 'TARM SGL' -> Read.
        """
        try:
            # Clear old data from buffer before starting
            self.ser.reset_input_buffer()

            # Trigger a single measurement
            self._write("TARM SGL")

            # Enable auto-read momentarily to get the data back
            self._write("++auto 1")

            # Read line, strip whitespace
            raw_data = self.ser.read_until(b'\n').strip()

            # Turn auto-read back off
            self._write("++auto 0")

            if not raw_data:
                raise ValueError("DMM returned empty data.")

            return float(raw_data.decode('utf-8'))

        except Exception as e:
            print(f"Error reading DMM: {e}")
            raise

    def close(self):
        """Closes the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
