"""
DUT setup utilities for ALSu PSC automated testing.

This module provides a `DUT` dataclass that:
- Prompts the operator for PSC identifiers (shipment number,
  serial number, PV prefix).

- Queries the PSC over EPICS to capture configuration (channels,
  resolution, bandwidth, polarity).

- Creates a per-shipment report directory and a timestamped
  raw-data subdirectory.
"""
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Tuple
from time import sleep
from EPICS_Adapters.psc_epics import PSC
from psc_models import PSCModel, get_psc_model_from_user


@dataclass
class DUT:
    """Represents the Device Under Test (PSC) and related file paths/state.

    Attributes:
        psc_sn: Zero-padded 4-digit PSC serial number (e.g., '0042').
        pv_prefix: EPICS PV prefix of the PSC (e.g., 'lab{3}').
        psc: EPICS adapter created after pv_prefix is known.
        model: PSCModel dataclass with parameters/limits for different models
        report_dir: Per-shipment report directory path.
        raw_data_dir: Timestamped raw-data subdirectory path for this run.
        num_channels: Number of PSC channels (queried from EPICS).
        resolution: Resolution mode string (queried from EPICS).
        bandwidth: Bandwidth mode string (queried from EPICS).
        polarity: Polarity mode string (queried from EPICS).
        shipment_num: Integer shipment identifier entered by the operator.
        dir_timestamp: Timestamp string used in raw-data directory naming.
    """
    # --- identifiers / adapter ---
    psc_sn: str = ""
    pv_prefix: str = ""
    psc: PSC | None = None
    model: PSCModel = field(init=False)

    # --- filesystem / run info ---
    report_dir: str = field(init=False, default="")
    raw_data_dir: str = field(init=False, default="")
    dir_timestamp: str = field(init=False, default="")

    # --- PSC configuration (populated from EPICS) ---
    num_channels: int = field(init=False, default=2)
    resolution: str = field(init=False, default="")
    bandwidth: str = field(init=False, default="")
    polarity: str = field(init=False, default="")

    # --- operator input ---
    shipment_num: int = field(init=False)

    def prompt_inputs(self):
        """Prompt user for basic DUT info.
           - Get shipment #, PSC sn, and PV prefix...
           - Build the PSC Adapter with that PV prefix
           - Get PSC configuration (PV Values)
           - Create directory structure, timestamps
        """
        self.shipment_num = self._get_shipment_num()
        self.psc_sn = self._get_psc_sn()
        self.pv_prefix = self._get_psc_pv_prefix()

        # Create the adapter...
        self.psc = PSC(prefix=self.pv_prefix)

        # Populate the configuration from the PSC PVs
        self.query_psc_config()

        # Get PSC Model from psc_models.py Function
        self.model = get_psc_model_from_user(self.num_channels)

        # Create directory structure...
        self.report_dir = \
            self.make_report_dir()
        self.raw_data_dir, self.dir_timestamp = \
            self.make_rawdata_subdir()

    def query_psc_config(self) -> None:
        """Get values from PSC about unit type from PVs"""
        if self.psc is None:
            raise RuntimeError("PSC adapter not initialized before \n"
                               "calling query_psc_config()")
        self.num_channels = self.psc.get_num_channels()
        self.resolution = self.psc.get_resolution()
        self.bandwidth = self.psc.get_bandwidth()
        self.polarity = self.psc.get_polarity()

        # Test that EEPROM Values aren't Zeroed...
        print("\n\n\n Reading EEPROM...")
        print(f"EEPROM # Of Channels: {self.num_channels}")
        print(f"EEPROM Resolution: {self.resolution}")
        print(f"EEPROM Bandwidth: {self.bandwidth}")
        print(f"EEPROM Polarity: {self.polarity}")
        print("\n\n\n")
        if self.num_channels not in [2, 4]:
            raise ConnectionError("Could not detect valid PSC channels at "
                                  f"{self.pv_prefix}. Check EEPROM is "
                                  "Configured, PSC is connected. ")
        if self.resolution[:2] not in ["HS", "MS"]:
            raise ConnectionError("Could not detect valid PSC at "
                                  f"{self.pv_prefix}. Check EEPROM is "
                                  "Configured, PSC is connected. ")
        if self.bandwidth[:1] not in ["S", "F"]:
            raise ConnectionError("Could not detect valid PSC at "
                                  f"{self.pv_prefix}. Check EEPROM is "
                                  "Configured, PSC is connected. ")
        if self.polarity[:1] not in ["B", "U"]:
            raise ConnectionError("Could not detect valid PSC at "
                                  f"{self.pv_prefix}. Check EEPROM is "
                                  "Configured, PSC is connected. ")

    def make_report_dir(self, base_dir="."):
        """Create shipment directory"""

        dir_name = f"Shipment #{self.shipment_num}"
        report_dir = os.path.join(base_dir, dir_name)
        os.makedirs(report_dir, exist_ok=True)
        return report_dir

    def make_rawdata_subdir(self) -> Tuple[str, str]:
        """Create a subdir under report_dir"""

        # Create timestamp...
        dir_timestamp = datetime.now().strftime(
            "%m-%d-%y_%H-%M")

        # build dir name...
        subdir_name = (f"{self.num_channels}ch_{self.resolution[:2]}"
                       f"{self.bandwidth[:1]}_SN{self.psc_sn}_RawData_"
                       f"{dir_timestamp}")
        raw_data_dir = os.path.join(
            self.report_dir, subdir_name)

        os.makedirs(raw_data_dir, exist_ok=True)

        return raw_data_dir, dir_timestamp

    def _get_shipment_num(self) -> int:
        """Prompt for the shipment number"""
        while True:
            shipment_num = input('\nEnter Shipment Number (Used for'
                                 'report directory): ')

            # Check if a digit was entered and re-prompt if not...
            if not shipment_num.isdigit():
                print("Shipment Number must be a numeric value")
                continue

            else:
                return int(shipment_num)

    def _get_psc_sn(self) -> str:
        """Prompt for the PSC S/N, add leading zero padding"""
        while True:
            psc_sn = input('\nEnter PSC serial number: (Enter "H" '
                           'for help):')
            # If Help...
            if psc_sn == "H":
                print("Serial Number is on the ITR document"
                      "attached to the PSC Chassis")
                continue

            # Check if a digit was entered and re-prompt if not...
            elif not psc_sn.isdigit():
                print("Serial number must be numeric, "
                      "between 0001 and 9999")
                continue

            # Check if digit between 1 and 9999...
            else:
                psc_sn = int(psc_sn)
                if not 1 <= psc_sn <= 9999:
                    print("Serial number must be numeric, "
                          "between 001 and 9999")
                    continue

            # Add leading zeroes to psc_sn...
            psc_sn = f"{psc_sn:04d}"
            return psc_sn

    def _get_psc_pv_prefix(self) -> str:
        """Prompt for PSC #, to make PV Prefix"""
        while True:
            psc_num = input("Enter the PSC Number under test "
                            "(e.g., for PSC 'lab{3}', enter "
                            "'3': ")

            # Check if numeric...
            if not psc_num.isdigit():
                print("PSC Number must be a numeric, "
                      "between 1 and 6")
                continue

            else:
                # Check if between 1 and 6...
                psc_num = int(psc_num)
                if not 1 <= psc_num <= 6:
                    print("Serial number must be numeric, "
                          "between 001 and 9999")
                    continue

            # psc_num is now confirmed to be valid...break
            break

        pv_prefix = f"lab{{{psc_num}}}"
        print(f"pv_prefix = {pv_prefix}")
        return pv_prefix

    def init(self):
        """Initialize the PSC in the absence of the sequencer"""
        assert self.psc is not None

        for chan in range(1, self.num_channels + 1):
            self.psc.set_power_on1(chan, 0)
            self.psc.set_enable_on2(chan, 0)
            sleep(0.5)
            self.psc.set_power_on1(chan, 1)
            self.psc.set_enable_on2(chan, 1)
