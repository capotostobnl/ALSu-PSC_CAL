"""f"""
import os
from time import sleep

from initialize_dut import DUT
from ate_init import ate_init
from EPICS_Adapters.ate_epics import ATE
from Instruments.hp_3458a import HP3458A


from psc_models import get_psc_model_from_user

from cal_report_generator import CalibrationReport

if __name__ == "__main__":

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
        psc_designation = psc_config.designation,
        serial_number=dut.psc_sn
    )

    report.write_header()











    def measure_testpoints(current, sp, chan, verbose):
        """f"""
        ate.set_cal_dac_w_os(current)
        if verbose:
            print("Adjusting DAC for null error")
        td = 2  # wait time after changing DAC
        i = 0
        dut.psc.set_dac_setpt(chan, sp)
        sleep(td)
        err = dut.psc.get_error_i(chan)  # Read Error Current Float Val
        while abs(err) > current_full_scale * 2 and i < 12 or i == 0:
            print(f"adjustment {i}")
            dac = sp - err/400 * p_scale_factor
            sp = dac
            dut.psc.set_dac_setpt(chan, sp)  # set DAC
            sleep(td)
            err = dut.psc.get_error_i(chan)  # Read Error Current Float Val
            i += 1

        adc1 = dut.psc.get_dcct1(chan)
        adc2 = dut.psc.get_dcct2(chan)
        adc3 = dut.psc.get_dac(chan)
        dmm_val = dmm.read_value() - dmm_offs # reference current i0
        return [dmm * s_scale_factor * p_scale_factor, dac, adc1, adc2, adc3, err]

    def compute_m_b(y0, y1):
        """
        Calculates slope (m) and intercept (b) for:
        DAC_SP (idx 1), DCCT1 (idx 2), DCCT2 (idx 3), DAC_RB (idx 4)
        
        Returns: [mdac, m1, m2, m3, bdac, b1, b2, b3]
        """
        m1 = (y1[2]-y0[2])/(y1[0]-y0[0])
        m2 = (y1[3]-y0[3])/(y1[0]-y0[0])
        m3 = (y1[4]-y0[4])/(y1[1]-y0[1])
        mdac = (y1[1]-y0[1])/(y1[0]-y0[0])
        b1 = y0[2]-m1*y0[0]
        b2 = y0[3]-m2*y0[0]
        b3 = y0[4]-m3*y0[1]
        bdac = y0[1]-mdac*y0[0]

        return -mdac, m1, m2, m3, -bdac, b1, b2, b3

    def print_testpoints(y, v):
    if(v=='v'):
        print(f"{'Itest':>14}{'dacSP':>14}{'dcct1':>14}{'dcct2':>14}{'dacRB':>14}{'err':>14}")
    print(f"{y[0]:>14.6f}{y[1]:>14.6f}{y[2]:>14.6f}{y[3]:>14.6f}{y[4]:>14.6f}{y[5]:>14.6f}")

    def fprint_testpoints(y, v):
        if(v=='v'):
            fp.write(f"{'Itest':>12}{'dacSP':>12}{'dcct1':>12}{'dcct2':>12}{'dacRB':>12}{'err':>12}\n")
        fp.write(f"{y[0]:>12.6f}{y[1]:>12.6f}{y[2]:>12.6f}{y[3]:>12.6f}{y[4]:>12.6f}{y[5]:>12.6f}\n")
###j = chan
    for chan in range(1, dut.num_channels+1):
        
        for chan_dex in range(1, dut.num_channels+1):
            #Set all channels OFF 
            dut.psc.set_power_on1(chan_dex, 0)
            
            #Set all channels on ATE to TEST mode
            ate.set_mode(chan_dex, 'TEST')
            ate.set_cal_dac(0)
            sleep(1)

        # Get DMM Zero Reading
        dmm_offs = float(dmm.read_value())
        print("DMM zero offset reading: {dmm_offs:.7f}")

        #Set chan to CAL mode
        ate.set_mode(chan, 'CAL')
        sleep(1)

        burden_value = getattr(psc_config.burden_resistors, f"ch{chan}")
        s_scale_factor = burden_value * 10.0  # V/A
        p_scale_factor = psc_config.ndcct/s_scale_factor  # PS scale factor A/V

        current_full_scale = 1.0/burden_value  # Max burden current
###I0 = zero_sp
###I1 = span_sp
        zero_sp = -1.0/psc_config.ndcct  # 1A
        sp0 = 1.0

        # Round to the nearest mA
        span_sp = -(float(round(current_full_scale * 0.9 * 1000)/1000))  

        sp1 = float(round(10 * p_scale_factor*0.9))

        y0 = np.zeros(6) # readbacks
        y1 = np.zeros(6)
        M = np.zeros((N,8)) # gains/offsets multiple runs
        if abs(span_sp) > 0.11:
            dmm.set_range(1.0)
        if abs(span_sp) <= 0.11:
            dmm.set_range(0.1)

        print(f"{dut.pv_prefix}:Chan{chan}")
        print(f"Burden resistor = {burden_value:3.4f}")
              
        #Scale factors
        val_vout  = getattr(psc_config.sf_vout, f"ch{chan}")
        val_spare = getattr(psc_config.sf_spare, f"ch{chan}")

        dut.psc.set_sf_ramp_rate(chan, 4.0)
        dut.psc.set_sf_dcct_scale(chan, p_scale_factor)
        dut.psc.set_sf_vout(chan, val_vout)
        dut.psc.set_sf_ignd(chan, 1.0)
        dut.psc.set_sf_spare(chan, val_spare)
        dut.psc.set_sf_regulator(chan, 1.0)
        dut.psc.set_sf_error(chan, 1.0)

        #Fault thresholds
        val_ovc1 = getattr(psc_config.ovc1_threshold, f"ch{chan}")
        val_ovc2 = getattr(psc_config.ovc2_threshold, f"ch{chan}")
        val_ovv  = getattr(psc_config.ovv_threshold, f"ch{chan}")
        
        dut.psc.set_threshold_ovc1(chan, val_ovc1)
        dut.psc.set_threshold_ovc2(chan, val_ovc2)
        dut.psc.set_threshold_ovv(chan, val_ovv)
        dut.psc.set_threshold_err1(chan, 10)
        dut.psc.set_threshold_err2(chan, 10)
        dut.psc.set_threshold_ignd(chan, 10)



        #Fault Count limits
        caput(psc+chan[j]+':OVC1_Flt_CntLim-SP', 0.01)
        caput(psc+chan[j]+':OVC2_Flt_CntLim-SP', 0.01)
        caput(psc+chan[j]+':OVV_Flt_CntLim-SP', 0.01)
        caput(psc+chan[j]+':ERR1_Flt_CntLim-SP', 0.1)
        caput(psc+chan[j]+':ERR2_Flt_CntLim-SP', 0.1)
        caput(psc+chan[j]+':IGND_Flt_CntLim-SP', 0.2)
        caput(psc+chan[j]+':DCCT_Flt_CntLim-SP', 0.2)
        caput(psc+chan[j]+':FLT1_Flt_CntLim-SP', 0.1)
        caput(psc+chan[j]+':FLT2_Flt_CntLim-SP', 3)
        caput(psc+chan[j]+':FLT3_Flt_CntLim-SP', 0.5)
        caput(psc+chan[j]+':ON_Flt_CntLim-SP', 3)
        caput(psc+chan[j]+':HeartBeat_Flt_CntLim-SP', 3)
            
        dut.psc.set_op_mode(ch, 3)  # Set jump mode 
        dut.psc.set_averaging(chan, 1)  # PSC Averaging Mode to 167 samples
###k = run
###N = psc_config.num_runs
        for run in range(psc_config.num_runs):  # Runs per channel
            print(f"\nRun #: {run+1}")
            dut.psc.reset_gains_offsets(chan)

            print("Measuring initial gains and offsets")
            if run == psc_config.num_runs - 1:
                report.write_line(f"{dut.pv_prefix}Chan{chan}")
                report.write_line(f"Burden resistor = {burden_value:3.4f}")
                report.write_line("\nMeasuring initial gains and offsets")
#### Note! Line 425 in original
            y0 = measure_testpoints(zero_sp, sp0, chan, 0) # [dmm dac adc1 adc2 adc3 err]
            print_testpoints(y0,'v')
            if run == psc_config.num_runs - 1:
                fprint_testpoints(y0,'v')
            
            #print("")
            #print("Measuring i1")       
            y1 = measure_testpoints(span_sp, sp1, chan, 0) # [dmm dac adc1 adc2 adc3 err]
            #print("   I      dacSP      dcct1      dcct2      dacRB      err")
            print_testpoints(y1,'')
            if run == psc_config.num_runs - 1:
                fprint_testpoints(y1,'')

            #Initial measured gains/offsets
            [mdac, m1, m2, m3, bdac, b1, b2, b3] = compute_m_b(y0, y1)

            print("")
            print(f"{'dacSP':>40}{'dcct1':>14}{'dcct2':>14}{'dacRB':>14}")
            
            print(f"{'Initial measured offsets: '}{bdac:>14.6f}{b1:>14.6f}"
                  f"{b2:>14.6f}{0:>14.6f}")  # initial measured offsets 
            
            print(f"{'Initial measured gains:   '}{mdac:>14.6f}{m1:>14.6f}"
                  f"{m2:>14.6f}{m3:>14.6f}")  # initial measured gains 
            
            print(f"{'Gain corrections:         '}{mdac:>14.6f}{1/m1:>14.6f}"
                  f"{1/m2:>14.6f}{1:>14.6f}") 
            #print initial measured gain errors in percent (gtarget-m1)/gtarget*100, (gtarget-m2)/gtarget*100 ... 

            print("")
            print("Writing gain and offset corrections for dacSP, dcct1, and dcct2 to PSC")
            
            if run == psc_config.num_runs - 1:
                report.write_line("")
                report.write_line(f"{'dacSP':>40}{'dcct1':>14}{'dcct2':>14}{'dacRB':>14}\n")
                report.write_line(f"{'Initial measured offsets: '}{bdac:>14.6f}{b1:>14.6f}{b2:>14.6f}{0:>14.6f}\n") #initial measured offsets
                report.write_line(f"{'Initial measured gains:   '}{mdac:>14.6f}{m1:>14.6f}{m2:>14.6f}{m3:>14.6f}\n") #initial measured gains 
                report.write_line(f"{'Gain corrections:         '}{mdac:>14.6f}{1/m1:>14.6f}{1/m2:>14.6f}{1:>14.6f}\n") 
                #print initial measured gain errors in percent (gtarget-m1)/gtarget*100, (gtarget-m2)/gtarget*100 ... 

                report.write_line("")
                report.write_line("Writing gain and offset corrections for dacSP, dcct1, and dcct2 to PSC\n")
            
            sleep(2)
            # offset constants are subtracted from ADC readings and DAC setpoint
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
            y0[4] = adc3
            print("DAC SP   DAC RB")
            print(f"{sp0:2.6f}   {y0[4]:2.6f} ")

            if run == psc_config.num_runs - 1:
                report.write_line("")
                report.write_line("Measuring DAC Readback gain and offset\n")
                report.write_line("DAC SP   DAC RB")
                report.write_line(f"{sp0:2.6f}   {y0[4]:2.6f} ")

