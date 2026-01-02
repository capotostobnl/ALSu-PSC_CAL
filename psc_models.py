"""
PSC Model Definitions and Selection Utilities.

This module defines the `PSCConfig` dataclass, which encapsulates the
hardware specifications and calibration parameters for various Power Supply
Controller (PSC) versions. It uses `ChannelValues` to explicitly map
settings to physical channels.
"""

import sys
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ChannelValues:
    """
    A per-channel data container for PSC hardware parameters.

    This class provides an explicit mapping of values (current, voltage,
    logic steps, or resistance) to physical PSC channels.

    Attributes:
        ch1: The parameter value assigned to Channel 1.
        ch2: The parameter value assigned to Channel 2.
        ch3: The parameter value assigned to Channel 3. Defaults to None.
        ch4: The parameter value assigned to Channel 4. Defaults to None.
    """
    ch1: float
    ch2: float
    ch3: Optional[float] = None
    ch4: Optional[float] = None

    def as_list(self) -> List[float]:
        """Returns the non-None values as a list."""
        vals = [self.ch1, self.ch2]
        if self.ch3 is not None:
            vals.append(self.ch3)
        if self.ch4 is not None:
            vals.append(self.ch4)
        return vals

    def get(self, index: int) -> float:
        """Retrieves value by 0-based index (0=ch1, 1=ch2, etc)."""
        return self.as_list()[index]


@dataclass(frozen=True)
class PSCConfig:
    """
    Represents the technical specifications and calibration limits for a
    specific PSC model.

    Attributes:
        model_id: Unique internal identifier (e.g., '1').
        display_name: Short name used for console menus (e.g., '2CH-HSS...').
        designation: Prefix for file naming (e.g., '2CH-HSS-AR-ABend-QFA_').
        ndcct: The number of turns in the DCCT.
        channels: The number of active channels (2 or 4).
        burden_resistors: ChannelValues for Rb (Ohms).
        sf_vout: ChannelValues for Vout Scale Factor.
        sf_spare: ChannelValues for Spare Scale Factor.
        ovc1_threshold: ChannelValues for Over-Current 1 Threshold (Amps).
        ovc2_threshold: ChannelValues for Over-Current 2 Threshold (Amps).
        ovv_threshold: ChannelValues for Over-Voltage Threshold (Volts).
        num_runs: Number of runs to take per channel
    """
    model_id: str
    display_name: str
    designation: str
    ndcct: float
    channels: int
    burden_resistors: ChannelValues
    sf_vout: ChannelValues
    sf_spare: ChannelValues
    ovc1_threshold: ChannelValues
    ovc2_threshold: ChannelValues
    ovv_threshold: ChannelValues
    num_runs: int = 5


# -----------------------------------------------------------------------------
# Model Definitions
# -----------------------------------------------------------------------------

MODELS = {
    # 2-Channel Units
    "ABend-QFA": PSCConfig(
        model_id="ABend-QFA",
        display_name="2CH-HSS-AR-ABend-QFA",
        designation="2CH-HSS-AR-ABend-QFA_",
        ndcct=2000.0,
        channels=2,
        burden_resistors=ChannelValues(ch1=4.5, ch2=9.0),
        sf_vout=ChannelValues(ch1=-47.5, ch2=-20.0),
        sf_spare=ChannelValues(ch1=-40.0, ch2=-20.0),
        ovc1_threshold=ChannelValues(ch1=390.0, ch2=195.0),
        ovc2_threshold=ChannelValues(ch1=390.0, ch2=195.0),
        ovv_threshold=ChannelValues(ch1=470.0, ch2=190.0),
    ),
    "AR-QD-QF": PSCConfig(
        model_id="AR-QD-QF",
        display_name="2CH-HSS-AR-QD-QF",
        designation="2CH-HSS-AR-QD-QF_",
        ndcct=1000.0,
        channels=2,
        burden_resistors=ChannelValues(ch1=18.0, ch2=9.0),
        sf_vout=ChannelValues(ch1=-1.25, ch2=-1.25),
        sf_spare=ChannelValues(ch1=-6.0, ch2=-12.0),
        ovc1_threshold=ChannelValues(ch1=51.0, ch2=101.0),
        ovc2_threshold=ChannelValues(ch1=51.0, ch2=101.0),
        ovv_threshold=ChannelValues(ch1=12.7, ch2=12.7),
    ),

    # 4-Channel Units

    "AR-Fast-XY-Corr": PSCConfig(
        model_id="AR-Fast-XY-Corr",
        display_name="4CH-MSF-AR-Fast XY Corr",
        designation="4CH-MSF-AR-Fast XY Corr_",
        ndcct=1000.0,
        channels=4,
        burden_resistors=ChannelValues(ch1=33.333333, ch2=33.333333,
                                       ch3=33.333333, ch4=33.333333),
        sf_vout=ChannelValues(ch1=1.9, ch2=1.9, ch3=1.9, ch4=1.9),
        sf_spare=ChannelValues(ch1=-5.0, ch2=-5.0, ch3=-5.0, ch4=-5.0),
        ovc1_threshold=ChannelValues(ch1=24.5, ch2=24.5, ch3=24.5, ch4=24.5),
        ovc2_threshold=ChannelValues(ch1=24.5, ch2=24.5, ch3=24.5, ch4=24.5),
        ovv_threshold=ChannelValues(ch1=18.5, ch2=18.5, ch3=18.5, ch4=18.5),
    ),
    "AR-Slow-XY-Corr": PSCConfig(
        model_id="AR-Slow-XY-Corr",
        display_name="4CH-MSS-AR Slow XY Corr",
        designation="4CH-MSS-AR Slow XY Corr_",
        ndcct=1000.0,
        channels=4,
        burden_resistors=ChannelValues(ch1=33.333333, ch2=33.333333,
                                       ch3=33.333333, ch4=33.333333),
        sf_vout=ChannelValues(ch1=1.9, ch2=1.9, ch3=1.9, ch4=1.9),
        sf_spare=ChannelValues(ch1=-5.0, ch2=-5.0, ch3=-5.0, ch4=-5.0),
        ovc1_threshold=ChannelValues(ch1=24.5, ch2=24.5, ch3=24.5, ch4=24.5),
        ovc2_threshold=ChannelValues(ch1=24.5, ch2=24.5, ch3=24.5, ch4=24.5),
        ovv_threshold=ChannelValues(ch1=18.5, ch2=18.5, ch3=18.5, ch4=18.5),
    ),
    "AR-SD-SF": PSCConfig(
        model_id="AR-SD-SF",
        display_name="4CH-MSS-AR-SD-SF",
        designation="4CH-MSS-AR-SD-SF_",
        ndcct=1000.0,
        channels=4,
        burden_resistors=ChannelValues(ch1=15.38462, ch2=7.14286,
                                       ch3=15.38462, ch4=7.14286),
        sf_vout=ChannelValues(ch1=-12.5, ch2=-10.0, ch3=-12.5, ch4=-10.0),
        sf_spare=ChannelValues(ch1=-8.0, ch2=-15.0, ch3=-8.0, ch4=-15.0),
        ovc1_threshold=ChannelValues(ch1=78.0, ch2=148.0, ch3=78.0, ch4=148.0),
        ovc2_threshold=ChannelValues(ch1=78.0, ch2=148.0, ch3=78.0, ch4=148.0),
        ovv_threshold=ChannelValues(ch1=120.0, ch2=95.0, ch3=120.0, ch4=95.0),
    ),
    "AR-SK": PSCConfig(
        model_id="AR-SK",
        display_name="4CH-MSS-AR-SK",
        designation="4CH-MSS-AR-SK_",
        ndcct=1000.0,
        channels=4,
        burden_resistors=ChannelValues(ch1=33.333333, ch2=33.333333,
                                       ch3=33.333333, ch4=33.333333),
        sf_vout=ChannelValues(ch1=1.9, ch2=1.9, ch3=1.9, ch4=1.9),
        sf_spare=ChannelValues(ch1=-5.0, ch2=-5.0, ch3=-5.0, ch4=-5.0),
        ovc1_threshold=ChannelValues(ch1=24.5, ch2=24.5, ch3=24.5, ch4=24.5),
        ovc2_threshold=ChannelValues(ch1=24.5, ch2=24.5, ch3=24.5, ch4=24.5),
        ovv_threshold=ChannelValues(ch1=18.5, ch2=18.5, ch3=18.5, ch4=18.5),
    ),
}


# -----------------------------------------------------------------------------
# Selection Utility
# -----------------------------------------------------------------------------

def get_psc_model_from_user(num_channels: int) -> PSCConfig:
    """
    Filters models by channel count and prompts operator with aligned columns.

    Args:
        num_channels: The integer number of detected channels (e.g., 2 or 4).

    Returns:
        PSCConfig: The selected configuration object.

    Raises:
        ValueError: If no models exist for the given channel count.
        SystemExit: If the user aborts selection.
    """

    available_models = [
        m for m in MODELS.values()
        if m.channels == num_channels
    ]

    if not available_models:
        raise ValueError(f"No models defined for {num_channels} channels.")

    # Calculate padding for aligned menu display
    max_label_len = max(len(f"'{m.display_name}'") for m in
                        available_models) + 2

    print(f"\n--- Select {num_channels}-Channel PSC Type ---")
    for i, model in enumerate(available_models, 1):
        label = f"'{model.display_name}'".ljust(max_label_len)
        print(f"{i}. {label} | {model.description}")

    while True:
        try:
            choice = input("\nEnter Type (or 'q' to quit): ").strip().lower()

            if choice == 'q':
                print("Testing aborted by operator.")
                sys.exit(0)

            idx = int(choice) - 1
            if 0 <= idx < len(available_models):
                selected = available_models[idx]
                print(f"--> Selected: {selected.display_name}\n")
                return selected

            print(f"Invalid choice. Select 1-{len(available_models)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nExecution interrupted by operator (Ctrl+C). Exiting...")
            sys.exit(0)
