"""ATE Initializtion Submodule
Modified M. Capotosto 11-9-2025
Original: T. Caracappa
"""

from time import sleep
from initialize_dut import DUT
from EPICS_Adapters.ate_epics import ATE


def ate_init(ate: ATE, dut: DUT) -> None:
    """f"""
    assert dut.psc is not None
    assert ate is not None
    sleep(0)
