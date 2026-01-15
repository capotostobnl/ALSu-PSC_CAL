"""f"""
import os
from time import sleep

import numpy as np
from initialize_dut import DUT
from ate_init import ate_init
from EPICS_Adapters.ate_epics import ATE
from Instruments.hp_3458a import HP3458A
from psc_models import get_psc_model_from_user
from cal_report_generator import CalibrationReport

###############################################################################
#   Logging
###############################################################################
HDR_6COL = (f"{'Itest':>14}{'dacSP':>14}{'dcct1':>14}{'dcct2':>14}"
            f"{'dacRB':>14}{'err':>14}")
HDR_4COL = f"{'dacSP':>40}{'dcct1':>14}{'dcct2':>14}{'dacRB':>14}"

class CalibrationLogger:
    def __init__(self):
        self.report_obj = None

    def set_report(self, report_obj):
        self.report_obj = report_obj

    def log(self, msg):
        print(msg)
        if self.report_obj:
            self.report_obj.write_line(f"{msg}\n")

logger = CalibrationLogger()

def log_report(msg=""):
    logger.log(msg)

###############################################################################
#   Measurements
###############################################################################

def measure_testpoints(ate_obj, dmm_obj, psc_hw, psc_config, current, sp, chan,
                       dmm_offset, verbose=False):
    """
    Performs a single test point measurement with iterative DAC adjustment.
    """
    # Prepare Hardware
    ate_obj.set_cal_dac_w_os(current)

    # Get physical limits from the CONFIG object
    full_scale = psc_config.get_current_full_scale(chan)
    p_scale = psc_config.get_p_scale_factor(chan)
    s_scale = psc_config.get_s_scale_factor(chan)

    if verbose:
        print("Adjusting DAC for null error")

    td = 2
    i = 0
    psc_hw.set_dac_setpt(chan, sp)
    sleep(td)

    err = psc_hw.get_error_i(chan)

    # Iterative Adjustment Loop
    while (abs(err) > full_scale * 2 and i < 12) or i == 0:
        if verbose:
            print(f"adjustment {i}")
        dac = sp - (err / 400) * p_scale
        sp = dac
        psc_hw.set_dac_setpt(chan, sp)
        sleep(td)
        err = psc_hw.get_error_i(chan)
        i += 1

    # Capture Readbacks
    adc1 = psc_hw.get_dcct1(chan)
    adc2 = psc_hw.get_dcct2(chan)
    adc3 = psc_hw.get_dac(chan)

    # Use the passed-in dmm_offset
    dmm_val = dmm_obj.read_value() - dmm_offset

    # Final Unit Conversion (A -> scaled values)
    return [dmm_val * s_scale * p_scale, dac, adc1, adc2, adc3, err]


def compute_m_b(y_low, y_high):
    """
    Calculates slope (m) and intercept (b) for:
    DAC_SP (idx 1), DCCT1 (idx 2), DCCT2 (idx 3), DAC_RB (idx 4)

    Returns: [mdac, m1, m2, m3, bdac, b1, b2, b3]
    """
    m1 = (y_high[2]-y_low[2])/(y_high[0]-y_low[0])
    m2 = (y_high[3]-y_low[3])/(y_high[0]-y_low[0])
    m3 = (y_high[4]-y_low[4])/(y_high[1]-y_low[1])
    mdac = (y_high[1]-y_low[1])/(y_high[0]-y_low[0])
    b1 = y_low[2]-m1*y_low[0]
    b2 = y_low[3]-m2*y_low[0]
    b3 = y_low[4]-m3*y_low[1]
    bdac = y_low[1]-mdac*y_low[0]

    return -mdac, m1, m2, m3, -bdac, b1, b2, b3

'''
def print_testpoints(y, v):
    """
    Prints formatted test data to the standard output (console).

    Args:
        y (list or np.array): A list containing 6 data points:
            [dmm_val, dac_setpoint, dcct1, dcct2, dac_readback, error].
        v (str): Verbosity flag. If set to 'v', prints the column
            header before the data row.
    """
    if v == 'v':
        print(f"{'Itest':>14}{'dacSP':>14}{'dcct1':>14}{'dcct2':>14}"
              f"{'dacRB':>14}{'err':>14}")
    print(f"{y[0]:>14.6f}{y[1]:>14.6f}{y[2]:>14.6f}{y[3]:>14.6f}"
          f"{y[4]:>14.6f}{y[5]:>14.6f}")


def fprint_testpoints(report_obj, y, v):
    """
    Writes formatted test data to the PDF calibration report.

    Args:
        y (list or np.array): A list containing 6 data points:
            [dmm_val, dac_setpoint, dcct1, dcct2, dac_readback, error].
        v (str): Verbosity flag. If set to 'v', writes the column
            header to the PDF before the data row.
    """
    if v == 'v':
        report_obj.write_line(f"{'Itest':>12}{'dacSP':>12}{'dcct1':>12}"
                              f"{'dcct2':>12}{'dacRB':>12}{'err':>12}\n")
    report_obj.write_line(f"{y[0]:>12.6f}{y[1]:>12.6f}{y[2]:>12.6f}"
                          f"{y[3]:>12.6f}{y[4]:>12.6f}{y[5]:>12.6f}\n")
'''

def main():
    # Instantiate DMM object, initialize DMM Settings
    dmm = HP3458A()
    dmm.dmm_init()

    ate = ATE(prefix="PSCtest:", ch_fmt="CH{ch}:")
    dut = DUT()  # Create DUT class instance
    ##############################################################
    # Get user inputs...Instantiate DUT
    ##############################################################

    # Prompt the user for PSC Info
    # Create Shipment directory, Report Gen Directory, and
    # Raw Data directories for this test run.
    dut.prompt_inputs()
    dut.init()

    psc_config = get_psc_model_from_user(dut.num_channels)

    ate_init(ate, dut)

    ##############################################################
    # Instantiate Report Generator...
    ##############################################################
    print(f"Calibrating PSC model {psc_config.designation} SN {dut.psc_sn}")

    pdf_filename = f"Calibration_{psc_config.designation}SN{dut.psc_sn}.pdf"
    pdf_path = os.path.join(dut.report_dir, pdf_filename)

    print(f"Generating Report at: {pdf_path}")

    report = CalibrationReport(
        filename=pdf_path,
        psc_designation=psc_config.designation,
        serial_number=dut.psc_sn
    )

    logger.set_report(report)
    report.write_header()

    ##############################################################

    # j = chan

    for chan in range(1, dut.num_channels+1):

        for chan_dex in range(1, dut.num_channels+1):
            # Set all channels OFF
            dut.psc.set_power_on1(chan_dex, 0)

            # Set all channels on ATE to TEST mode
            ate.set_mode(chan_dex, 'TEST')
            ate.set_cal_dac(0)
            sleep(1)

        # Get DMM Zero Reading
        dmm_offs = float(dmm.read_value())
        print("DMM zero offset reading: {dmm_offs:.7f}")

        # Set chan to CAL mode
        ate.set_mode(chan, 'CAL')
        sleep(1)

        current_full_scale = psc_config.get_current_full_scale(chan)
        burden_value = getattr(psc_config.burden_resistors, f"ch{chan}")
        p_scale_factor = psc_config.get_p_scale_factor(chan)

        # I0 = zero_sp
        # I1 = span_sp
        zero_sp = -1.0/psc_config.ndcct  # 1A
        sp0 = psc_config.sp0

        # Round to the nearest mA
        span_sp = -(float(round(current_full_scale * 0.9 * 1000)/1000))

        sp1 = float(round(10 * p_scale_factor*0.9))

        y_low = np.zeros(6)  # readbacks
        y_high = np.zeros(6)
        M = np.zeros((psc_config.num_runs, 8))  # gains/offsets multiple runs
        if abs(span_sp) > 0.11:
            dmm.set_range(1.0)
        if abs(span_sp) <= 0.11:
            dmm.set_range(0.1)

        print(f"{dut.pv_prefix}:Chan{chan}")
        print(f"Burden resistor = {burden_value:3.4f}")

        # Scale factors
        dcct_val = psc_config.sf_dcct_scale if psc_config.sf_dcct_scale \
            is not None else p_scale_factor

        static_sf = {
            "set_sf_dcct_scale": dcct_val,
            "set_sf_ramp_rate": psc_config.sf_ramp_rate,
            "set_sf_ignd": psc_config.sf_ignd,
            "set_sf_regulator": psc_config.sf_regulator,
            "set_sf_error": psc_config.sf_error,
        }

        for method, value in static_sf.items():
            getattr(dut.psc, method)(chan, value)

        # 3. Map of "Channel-Specific" scale factors (pulls ch1, ch2, etc.)
        channel_sf = {
            "sf_vout": "set_sf_vout",
            "sf_spare": "set_sf_spare",
        }

        for attr, method in channel_sf.items():
            # Gets the ChannelValues object, then gets the specific chX value
            value = getattr(getattr(psc_config, attr), f"ch{chan}")
            getattr(dut.psc, method)(chan, value)

        # Fault thresholds

        # Single-value thresholds
        simple_thresholds = {
            "err1_threshold": "set_threshold_err1",
            "err2_threshold": "set_threshold_err2",
            "ignd_threshold": "set_threshold_ignd",
        }

        for attr, method in simple_thresholds.items():
            getattr(dut.psc, method)(chan, getattr(psc_config, attr))

        # Channel-specific thresholds (ovc1, ovc2, ovv)
        multi_thresholds = {
            "ovc1_threshold": "set_threshold_ovc1",
            "ovc2_threshold": "set_threshold_ovc2",
            "ovv_threshold": "set_threshold_ovv",
        }

        for attr, method in multi_thresholds.items():
            # This handles the psc_config.ovc1_threshold.ch{chan} logic
            channel_data = getattr(psc_config, attr)
            value = getattr(channel_data, f"ch{chan}")
            getattr(dut.psc, method)(chan, value)

        # Fault Count limits
        fault_limits = {
            "ovc1_flt_cnt": "set_count_limit_ovc1",
            "ovc2_flt_cnt": "set_count_limit_ovc2",
            "ovv_flt_cnt": "set_count_limit_ovv",
            "err1_flt_cnt": "set_count_limit_err1",
            "err2_flt_cnt": "set_count_limit_err2",
            "ignd_flt_cnt": "set_count_limit_ignd",
            "dcct_flt_cnt": "set_count_limit_dcct",
            "flt1_flt_cnt": "set_count_limit_flt1",
            "flt2_flt_cnt": "set_count_limit_flt2",
            "flt3_flt_cnt": "set_count_limit_flt3",
            "flt_on_cnt": "set_count_limit_on",
            "flt_heartbeat_cnt": "set_count_limit_heartbeat"
        }

        # Loop through the dictionary to set all limits automatically
        for config_attr, method_name in fault_limits.items():
            value = getattr(psc_config, config_attr)
            getattr(dut.psc, method_name)(chan, value)

        dut.psc.set_op_mode(chan, 3)  # Set jump mode
        dut.psc.set_averaging(chan, 1)  # PSC Averaging Mode to 167 samples

        for run in range(psc_config.num_runs):  # Runs per channel
            print(f"\nRun #: {run+1}")
            dut.psc.reset_gains_offsets(chan)

            print("Measuring initial gains and offsets")
            if run == psc_config.num_runs - 1:
                report.write_line(f"{dut.pv_prefix}Chan{chan}")
                report.write_line(f"Burden resistor = {burden_value:3.4f}")
                report.write_line("\nMeasuring initial gains and offsets")

            y_low = measure_testpoints(
                ate_obj=ate,
                dmm_obj=dmm,
                psc_hw=dut.psc,
                psc_config=psc_config,
                current=zero_sp,
                sp=sp0,
                chan=chan,
                dmm_offset=dmm_offs,
                verbose=False
                )

            #Print testpoints
            if run == psc_config.num_runs - 1:
                log_report(HDR_6COL)
            log_report(
                f"{y_low[0]:>14.6f}{y_low[1]:>14.6f}{y_low[2]:>14.6f}"
                f"{y_low[3]:>14.6f}{y_low[4]:>14.6f}{y_low[5]:>14.6f}"
            )


            y_high = measure_testpoints(
                ate_obj=ate,
                dmm_obj=dmm,
                psc_hw=dut.psc,
                psc_config=psc_config,
                current=span_sp,
                sp=sp0,
                chan=chan,
                dmm_offset=dmm_offs,
                verbose=False
                )

            if run == psc_config.num_runs - 1:
                # Formatted data string for testpoints
                log_report(
                    f"{y_high[0]:>14.6f}{y_high[1]:>14.6f}"
                    f"{y_high[2]:>14.6f}{y_high[3]:>14.6f}"
                    f"{y_high[4]:>14.6f}{y_high[5]:>14.6f}"
                           )

            # Initial measured gains/offsets
            [mdac, m1, m2, m3, bdac, b1, b2, b3] = compute_m_b(y_low, y_high)

            if run == psc_config.num_runs - 1:
                log_report("")
                log_report(HDR_4COL)

                # initial measured offsets
                log_report(f"{'Initial measured offsets: '}{bdac:>14.6f}"
                           f"{b1:>14.6f}{b2:>14.6f}{0:>14.6f}")

                # initial measured gains
                log_report(f"{'Initial measured gains:   '}{mdac:>14.6f}"
                           f"{m1:>14.6f}{m2:>14.6f}{m3:>14.6f}")

                log_report(f"{'Gain corrections:         '}{mdac:>14.6f}"
                           f"{1/m1:>14.6f}{1/m2:>14.6f}{1:>14.6f}")

                log_report("")
                log_report("Writing gain and offset corrections for dacSP,"
                           " dcct1, and dcct2 to PSC")

            sleep(2)
            # offset constants are subtracted from ADC readings and
            # DAC setpoint
            # write m1, m2, mdac, b1, b2, bdac to PSC (do not write m3, b3)
            dut.psc.set_gain_dcct1(chan, 1/m1)
            dut.psc.set_gain_dcct2(chan, 1/m2)
            dut.psc.set_gain_dac_setpoint(chan, mdac)
            dut.psc.set_offset_dcct1(chan, b1)
            dut.psc.set_offset_dcct2(chan, b2)
            dut.psc.set_offset_dac_setpoint(chan, bdac)

            print("")
            print("Measuring DAC Readback gain and offset")

            dut.psc.set_dac_setpt(chan, sp0)
            sleep(1)
            adc3 = dut.psc.get_dac(chan)
            y_low[4] = adc3
            print("DAC SP   DAC RB")
            print(f"{sp0:2.6f}   {y_low[4]:2.6f} ")

            if run == psc_config.num_runs - 1:
                report.write_line("")
                report.write_line("Measuring DAC Readback gain and offset\n")
                report.write_line("DAC SP   DAC RB")
                report.write_line(f"{sp0:2.6f}   {y_low[4]:2.6f} ")

            dut.psc.set_dac_setpt(chan, sp1)
            sleep(1)
            adc3 = dut.psc.get_dac(chan)
            y_high[4] = adc3
            print(f"{sp1:2.6f}   {y_high[4]:2.6f} ", end="")
            print("")
            if run == psc_config.num_runs - 1:
                report.write_line(f"{sp1:2.6f}   {y_high[4]:2.6f} \n")

            m3 = (y_high[4]-y_low[4])/(sp1-sp0)
            b3 = y_low[4]-m3*sp0

            print(f"Measured offset: {b3}")
            print(f"Measured gain: {m3}")
            print(f"Gain correction: {1/m3}")

            print("")
            print("Writing gain and offset constants for dacRB to PSC")
            sleep(2)

            # write m3, b3 to PSC
            dut.psc.set_gain_dac_setpoint(chan, 1/m3)
            dut.psc.set_offset_dac_setpoint(chan, b3)

            if run == psc_config.num_runs - 1:
                report.write_line("")
                report.write_line(f"Measured offset: {b3}\n")
                report.write_line(f"Measured gain: {m3}\n")
                report.write_line(f"Gain Correction: {1/m3}\n")
                report.write_line("Writing gain and offset constants for dacRB"
                                " to PSC\n\n")

            # Verification
            print("\n\nVerification")
            if run == psc_config.num_runs - 1:
                report.write_line("Verification")

            # [dmm dac adc1 adc2 adc3 err]
            y_low = measure_testpoints(
                ate_obj=ate,
                dmm_obj=dmm,
                psc_hw=dut.psc,
                psc_config=psc_config,
                current=zero_sp,
                sp=sp0,
                chan=chan,
                dmm_offset=dmm_offs,
                verbose=False
                )
            print_testpoints(y_low, 'v')
            if run == psc_config.num_runs - 1:
                fprint_testpoints(report, y_low, 'v')

            # [dmm dac adc1 adc2 adc3 err]
            y_high = measure_testpoints(
                ate_obj=ate,
                dmm_obj=dmm,
                psc_hw=dut.psc,
                psc_config=psc_config,
                current=span_sp,
                sp=sp0,
                chan=chan,
                dmm_offset=dmm_offs,
                verbose=False
                )
            print_testpoints(y_high, '')
            if run == psc_config.num_runs - 1:
                fprint_testpoints(report, y_high, '')

            # Final measured gains/offsets
            [mdac, m1, m2, m3, bdac, b1, b2, b3] = compute_m_b(y_low, y_high)

            print("")
            print("")
            print(f"{'dacSP':>38}{'dcct1':>14}{'dcct2':>14}{'dacRB':>14}")
            print(f"{'Final measured offsets: '}{bdac:>14.6f}{b1:>14.6f}"
                f"{b2:>14.6f}{b3:>14.6f}")
            print(f"{'Final measured gains:   '}{mdac:>14.6f}{m1:>14.6f}"
                f"{m2:>14.6f}{m3:>14.6f}")
            # print initial measured gain errors in percent (gtarget-m1)/
            # gtarget*100, (gtarget-m2)/gtarget*100 ...
            print("\n\n")

            if run == psc_config.num_runs - 1:
                report.write_line("\n")
                report.write_line("\n")
                report.write_line(f"{'dacSP':>38}{'dcct1':>14}{'dcct2':>14}"
                                f"{'dacRB':>14}\n")
                report.write_line(f"{'Final measured offsets: '}{bdac:>14.6f}"
                                f"{b1:>14.6f}{b2:>14.6f}{b3:>14.6f}\n")
                report.write_line(f"{'Final measured gains:   '}{mdac:>14.6f}"
                                f"{m1:>14.6f}{m2:>14.6f}{m3:>14.6f}\n")
                # fp.write initial measured gain errors in percent (gtarget-m1)
                # /gtarget*100, (gtarget-m2)/gtarget*100 ...
                report.write_line("\n\n")

            M[run, :] = [mdac, m1, m2, m3, bdac, b1, b2, b3]

        # 0 is mean of each column. 1 is mean of each row
        Mavg = np.mean(M, axis=0)
        Mstd = np.std(M, axis=0)
        print("")
        print("")
        print("")
        print(f"{'dacSP':>38}{'dcct1':>14}{'dcct2':>14}{'dacRB':>14}")
        print(f"{'Final meas. offsets mean: '}{Mavg[4]:>9.6f}{Mavg[5]:>14.6f}"
            f"{Mavg[6]:>14.6f}{Mavg[7]:>14.6f}")
        print(f"{'Final meas. offsets stdev:'}{Mstd[4]:>9.6f}{Mstd[5]:>14.6f}"
            f"{Mstd[6]:>14.6f}{Mstd[7]:>14.6f}")
        print(f"{'Final meas. gains mean:   '}{Mavg[0]:>9.6f}{Mavg[1]:>14.6f}"
            f"{Mavg[2]:>14.6f}{Mavg[3]:>14.6f}")
        print(f"{'Final meas. gains stdev:  '}{Mstd[0]:>9.6f}{Mstd[1]:>14.6f}"
            f"{Mstd[2]:>14.6f}{Mstd[3]:>14.6f}")

        # print initial measured gain errors in percent (gtarget-m1)/gtarget
        # *100, (gtarget-m2)/gtarget*100 ...
        print("")

        report.write_line("\n")
        report.write_line(f"{'dacSP':>38}{'dcct1':>14}{'dcct2':>14}"
                        f"{'dacRB':>14}\n")
        report.write_line(f"{'Final measured offsets mean: '}{Mavg[4]:>9.6f}"
                        f"{Mavg[5]:>14.6f}{Mavg[6]:>14.6f}"
                        f"{Mavg[7]:>14.6f}\n")
        report.write_line(f"{'Final measured offsets stdev:'}{Mstd[4]:>9.6f}"
                        f"{Mstd[5]:>14.6f}{Mstd[6]:>14.6f}"
                        f"{Mstd[7]:>14.6f}\n")
        report.write_line(f"{'Final measured gains mean:   '}{Mavg[0]:>9.6f}"
                        f"{Mavg[1]:>14.6f}{Mavg[2]:>14.6f}"
                        f"{Mavg[3]:>14.6f}\n")
        report.write_line(f"{'Final measured gains stdev:  '}{Mstd[0]:>9.6f}"
                        f"{Mstd[1]:>14.6f}{Mstd[2]:>14.6f}"
                        f"{Mstd[3]:>14.6f}\n")
        report.write_line("\n")

        print(f"Saving channel {chan} calibration data to qspi\n")
        report.write_line(f"Saving channel {chan} calibration "
                        "constants to qspi\n")
        dut.psc.write_qspi(chan)

    if chan > 0:
        report.write_line("\n\n\n\n\n")
    if chan == dut.num_channels:
        report.write_line("Test data reviewed by ________________________"
                        "______   Date_____________")
    report.write_line("\n\n")
    report.write_line(f"\nPage {chan} of {dut.num_channels}")
    if chan < dut.num_channels:
        report.write_line("\f")  # form feed aka page break

    print("Calibration complete.")


if __name__ == "__main__":
    main()
