#!/usr/bin/env python3
"""
epics_test_report.py

Performs DAC loopback, EVR test and waveform captures, saves to HDF5, and generates a PDF report.
Configure LAB_INDEX at top to substitute every instance of 'lab{1}' -> 'lab{<LAB_INDEX>}'.
"""

import time
import sys
import os
import traceback
from datetime import datetime

# External libs
try:
    from epics import caget, caput, PV
except Exception:
    print("ERROR: pyepics (epics) not available. Install with `pip install pyepics`.")
    raise
import numpy as np
import h5py
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image, PageBreak

# ----------------- CONFIGURATION -----------------
# Change this to the lab number you want (1,2,3,...). This will replace 'lab{1}' tokens.
LAB_INDEX = 1
SN = '0025'

# File outputs
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
HDF5_FILENAME = f"epics_test_SN{SN}_{LAB_INDEX}_{TIMESTAMP}.h5"
REPORT_FILENAME = f"epics_test_report_SN{SN}_{LAB_INDEX}_{TIMESTAMP}.pdf"
PLOTS_DIR = f"plots_SN{SN}_{LAB_INDEX}_{TIMESTAMP}"
os.makedirs(PLOTS_DIR, exist_ok=True)

# Tolerances and timings
DAC_TARGET = 1.0
DAC_TOLERANCE = 0.1
SLEEP_AFTER_SET_SEC = 3
EVR_MONOTONIC_SECONDS = 10
BASELINE_WAIT = 15
STEP_WAIT = 5
RAMP_WAIT = 15

# Channels to attempt (we'll reduce to 2 if NumChannels-Mode reads as '2')
DEFAULT_CHANNELS = [1, 2, 3, 4]
# -------------------------------------------------

def lab_replace(pv_template):
    """Replace literal 'lab{1}' in the template with 'lab{N}' where N is LAB_INDEX."""
    return pv_template.replace('lab{1}', f'lab{{{LAB_INDEX}}}')

def safe_caget(name, timeout=5.0):
    """Wrapper around caget to return value or None and log errors."""
    try:
        val = caget(name, timeout=timeout)
        return val
    except Exception as e:
        print(f"caget ERROR for {name}: {e}")
        return None

def safe_caput(name, val, wait=True, timeout=5.0):
    """Wrapper around caput."""
    try:
        r = caput(name, val, wait=wait, timeout=timeout)
        return r
    except Exception as e:
        print(f"caput ERROR for {name} <- {val}: {e}")
        return False

def read_pv_array(name):
    """Attempt to read a PV that returns a waveform/array."""
    try:
        pv = PV(name)
        # allow a short wait for array to arrive
        time.sleep(0.05)
        arr = pv.get(as_numpy=True)
        # Convert to numpy array if possible
        if arr is None:
            return None
        return np.array(arr)
    except Exception as e:
        print(f"read_pv_array ERROR for {name}: {e}")
        return None

def plot_and_save(y, title, filename):
    """Plot y vs index, save to filename using matplotlib."""
    try:
        plt.figure(figsize=(6,3))
        plt.plot(np.arange(len(y)), y)
        plt.title(title)
        plt.xlabel("Sample")
        plt.ylabel("Value")
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return True
    except Exception as e:
        print(f"Plotting failed for {title}: {e}")
        return False

def monotonic_increasing(seq):
    """Return True if sequence is non-decreasing strictly increasing (monotonic). Allow equal steps."""
    if seq is None or len(seq) == 0:
        return False
    return all(x2 >= x1 for x1, x2 in zip(seq, seq[1:]))

def pv_template_list_for_channel(channel):
    """Return list of user waveform PV templates for a channel."""
    base = f"lab{{1}}Chan{channel}:USR:"
    items = ["DCCT1-Wfm", "DCCT2-Wfm", "DAC-Wfm", "Volt-Wfm", "Gnd-Wfm", "Spare-Wfm", "Reg-Wfm", "Error-Wfm"]
    return [base + item for item in items]

# List of PVs for the top-of-report table (templates)
TABLE_PV_TEMPLATES = [
    "lab{1}NumChannels-Mode",
    "lab{1}Resolution-Mode",
    "lab{1}Bandwidth-Mode",
    "lab{1}Polarity-Mode",
]

# Section 1 DAC set/get PV templates
DAC_SET_PV_TEMPLATES = [
    "lab{1}Chan1:DAC_SetPt-SP",
    "lab{1}Chan2:DAC_SetPt-SP",
    "lab{1}Chan3:DAC_SetPt-SP",
    "lab{1}Chan4:DAC_SetPt-SP",
]
DAC_READ_PV_TEMPLATES = [
    "lab{1}Chan1:DAC-I",
    "lab{1}Chan2:DAC-I",
    "lab{1}Chan3:DAC-I",
    "lab{1}Chan4:DAC-I",
]

# EVR PV
EVR_PV_TEMPLATE = "lab{1}TS-S-I"

# Section 3 control PVs templates
DIGOUT_ON2_TEMPLATES = [f"lab{{1}}Chan{ch}:DigOut_ON2-SP" for ch in [1,2,3,4]]
DIGOUT_PARK_TEMPLATES = [f"lab{{1}}Chan{ch}:DigOut_Park-SP" for ch in [1,2,3,4]]
DIGOUT_ON1_TEMPLATES = [f"lab{{1}}Chan{ch}:DigOut_ON1-SP" for ch in [1,2,3,4]]
SS_TRIG_TEMPLATE1 = "lab{1}Chan1:SS:Trig:Usr"  # snapshot trigger 
SS_TRIG_TEMPLATE2 = "lab{1}Chan2:SS:Trig:Usr"  # snapshot trigger 
SS_TRIG_TEMPLATE3 = "lab{1}Chan3:SS:Trig:Usr"  # snapshot trigger 
SS_TRIG_TEMPLATE4 = "lab{1}Chan4:SS:Trig:Usr"  # snapshot trigger 

# FOFB related
FOFB_IP_PV_TEMPLATE = "lab{1}FOFB:IPaddr-SP"
FOFB_FASTADDR_TEMPLATES = [
    "lab{1}Chan1:FOFB:FastAddr-SP",
    "lab{1}Chan2:FOFB:FastAddr-SP",
    "lab{1}Chan3:FOFB:FastAddr-SP",
    "lab{1}Chan4:FOFB:FastAddr-SP",
]

def main():
    print(f"Starting EPICS test script for lab{{{LAB_INDEX}}} at {datetime.now()}")
    report_elements = []
    styles = getSampleStyleSheet()
    now_str = datetime.now().isoformat()
    header_para = Paragraph(f"<b>EPICS Test Report</b><br/>SN{SN} lab{{{LAB_INDEX}}}<br/>{now_str}", styles['Title'])
    report_elements.append(header_para)
    report_elements.append(Spacer(1,12))

    # Open HDF5 file
    h5 = h5py.File(HDF5_FILENAME, "w")
    h5.attrs['generated_by'] = "epics_test_report.py"
    h5.attrs['lab'] = f"lab{{{LAB_INDEX}}}"
    h5.attrs['generated_at'] = now_str

    # ---- Top Table: read small set of PVs ----
    table_data = [["PV", "Value"]]
    print("Gathering table PVs...")
    for tmpl in TABLE_PV_TEMPLATES:
        pvname = lab_replace(tmpl)
        #val = safe_caget(pvname)
        val = caget(pvname, as_string=True)
        print(val)
        table_data.append([pvname, str(val)])
        # store into hdf5 attrs
        safe_name = pvname.replace(":", "_")
        try:
            h5.create_dataset(f"meta/{safe_name}", data=str(val))
        except Exception:
            try:
                h5["meta"].attrs[safe_name] = str(val)
            except Exception:
                pass

    t = Table(table_data, colWidths=[300, 200])
    t.setStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ])
    report_elements.append(Paragraph("<b>Device configuration</b>", styles['Heading2']))
    report_elements.append(t)
    report_elements.append(Spacer(1,12))

    # Decide channels based on NumChannels-Mode
    numchannels_val = safe_caget(lab_replace(TABLE_PV_TEMPLATES[0]))
    try:
        numchannels = int(str(numchannels_val)) if numchannels_val is not None else len(DEFAULT_CHANNELS)
    except Exception:
        numchannels = len(DEFAULT_CHANNELS)
    if numchannels not in (2,4):
        # default to 4 if unknown
        numchannels = 2
    channels = [1,2] if numchannels == 2 else [1,2,3,4]
    print(f"Detected NumChannels = {numchannels}. Using channels: {channels}")

    # ---------------- Section 1: DAC loopback test ----------------
    report_elements.append(Paragraph("<b>Section 1: DAC loopback test</b>", styles['Heading2']))
    print("Starting DAC loopback test: setting DAC setpoints to 1.0 ...")
    # Set all DAC setpoints to 1.0 for active channels
    for ch in channels:
        pvset = lab_replace(f"lab{{1}}Chan{ch}:DAC_SetPt-SP")
        print(pvset)
        safe_caput(pvset, DAC_TARGET)

    # Wait
    print(f"Waiting {SLEEP_AFTER_SET_SEC}s for values to settle...")
    time.sleep(SLEEP_AFTER_SET_SEC)

    # Read DAC readbacks and check tolerance
    dac_results = []
    any_fail = False
    read_table = [["Channel", "Readback", "Pass/Fail"]]
    for ch in channels:
        readpv = lab_replace(f"lab{{1}}Chan{ch}:DAC-I")
        val = safe_caget(readpv)
        try:
            val_f = float(val)
            passed = abs(val_f - DAC_TARGET) <= DAC_TOLERANCE
        except Exception:
            val_f = None
            passed = False
        status = "PASS" if passed else "FAIL"
        read_table.append([f"Chan{ch}", str(val_f), status])
        dac_results.append((ch, val_f, passed))
        if not passed:
            any_fail = True
        print(f"Channel {ch} readback {val_f} -> {status}")

    # Add DAC results table to report
    t2 = Table(read_table, colWidths=[120, 160, 120])
    t2.setStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black),
                 ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)])
    report_elements.append(t2)
    report_elements.append(Spacer(1,12))

    # If any failed, set setpoints back to zero and abort script
    print("Resetting DAC setpoints to 0.0...")
    for ch in channels:
        pvset = lab_replace(f"lab{{1}}Chan{ch}:DAC_SetPt-SP")
        safe_caput(pvset, 0.0)

    if any_fail:
        msg = Paragraph("<b>DAC loopback test failed on one or more channels. Aborting further tests.</b>", styles['Normal'])
        report_elements.append(msg)
        # close hdf5, write PDF and exit
        h5.close()
        doc = SimpleDocTemplate(REPORT_FILENAME, pagesize=letter)
        doc.build(report_elements)
        print("Report written to", REPORT_FILENAME)
        print("HDF5 written to", HDF5_FILENAME)
        sys.exit(1)

    # ---------------- Section 2: EVR monotonic test ----------------
    report_elements.append(Paragraph("<b>Section 2: EVR monotonicity test</b>", styles['Heading2']))
    evr_pv = lab_replace(EVR_PV_TEMPLATE)
    print(f"Running EVR monotonic test on {evr_pv} for {EVR_MONOTONIC_SECONDS}s...")
    samples = []
    start_t = time.time()
    while time.time() - start_t < EVR_MONOTONIC_SECONDS:
        v = safe_caget(evr_pv)
        try:
            samples.append(float(v))
        except Exception:
            samples.append(None)
        time.sleep(0.5)
    # Filter None
    samples_filtered = [s for s in samples if s is not None]
    evr_pass = monotonic_increasing(samples_filtered)
    evr_status = "PASS" if evr_pass else "FAIL"
    report_elements.append(Paragraph(f"EVR PV: {evr_pv} monotonic test -> <b>{evr_status}</b>", styles['Normal']))
    print(f"EVR Test {evr_status}")

    # Save EVR samples to hdf5
    try:
        h5.create_dataset("evr/samples", data=np.array([np.nan if s is None else s for s in samples]))
    except Exception as e:
        print("HDF5 write evr failed:", e)

    # Plot EVR sequence
    evr_plot = os.path.join(PLOTS_DIR, "evr_sequence.png")
    if len(samples_filtered) > 0:
        plot_and_save(samples_filtered, f"EVR {evr_pv}", evr_plot)
        report_elements.append(Image(evr_plot, width=400, height=150))
        report_elements.append(Spacer(1,12))

    # ---------------- Section 3: Test Data ----------------
    report_elements.append(Paragraph("<b>Section 3: Test Data</b>", styles['Heading2']))
    
        #Set Ramp rate to 10 Amps/Sec
    safe_caput("lab{1}Chan1:SF:AmpsperSec-SP",10)
    safe_caput("lab{1}Chan2:SF:AmpsperSec-SP",10)



    # Initialize - set DACs to zero
    print("Initializing: setting DACs to zero and preparing outputs...")
    for ch in channels:
        safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_SetPt-SP"), 0.0)
    # Set Enable High
    for pv in DIGOUT_ON2_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 1)
    # Set Park High
    for pv in DIGOUT_PARK_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 1)
    # Turn on Supply Set On1 High
    for pv in DIGOUT_ON1_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 1)

    print("Waiting 10s after enabling supplies...")
    time.sleep(10)

    # Set Park Low
    for pv in DIGOUT_PARK_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 0)

    print("Waiting 12s...")
    time.sleep(12)

    # Take snapshot at baseline
    print("Triggering baseline snapshot...")
    safe_caput(SS_TRIG_TEMPLATE1,1)
    safe_caput(SS_TRIG_TEMPLATE2,1)
    safe_caput(SS_TRIG_TEMPLATE3,1)
    safe_caput(SS_TRIG_TEMPLATE4,1)
    print(f"Waiting {BASELINE_WAIT}s for the snapshot to complete...")
    time.sleep(BASELINE_WAIT)


    # ---- Step response: Set DAC to 10.0, mode jump, set to 10.05, snapshot etc. ----
    print("Starting step response sequence...")  
    
    # Set Park High to clear integrator
    for pv in DIGOUT_PARK_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 1)
    time.sleep(5)
        
    # Set Park Low 
    for pv in DIGOUT_PARK_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 0)
    time.sleep(10)    
    
    
    # Caput 0.0
    for ch in channels:
    	safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_SetPt-SP"), 0.5)
    time.sleep(15)
    
    #First ramp up to current caput Ch`1 30.0 Ch 2 50
    safe_caput(lab_replace(f"lab{{1}}Chan1:DAC_SetPt-SP"), 30.0)
    safe_caput(lab_replace(f"lab{{1}}Chan2:DAC_SetPt-SP"), 50.0)
    time.sleep(20)
       
    # Set to jump mode (opmode = 3 
    for ch in channels:
        safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_OpMode-SP"), 3)
    time.sleep(8)
    # Caput 30.05 and 50.05 into setpoints
    #for ch in channels:
    safe_caput(lab_replace(f"lab{{1}}Chan1:DAC_SetPt-SP"), 30.05)
    safe_caput(lab_replace(f"lab{{1}}Chan2:DAC_SetPt-SP"), 50.05)
          
    # snapshot for step response
    print("Triggering step response snapshot...")
    safe_caput(SS_TRIG_TEMPLATE1,1)
    safe_caput(SS_TRIG_TEMPLATE2,1)
    safe_caput(SS_TRIG_TEMPLATE3,1)
    safe_caput(SS_TRIG_TEMPLATE4,1)
    time.sleep(STEP_WAIT)
    time.sleep(5)

    # Pull step response waveforms
    step_group = h5.require_group("step")
    for ch in channels:
        pv_templates = pv_template_list_for_channel(ch)
        for tmpl in pv_templates:
            pvname = lab_replace(tmpl)
            arr = read_pv_array(pvname)
            dsname = f"step/Chan{ch}/{pvname.replace(':','_')}"
            try:
                if arr is None:
                    step_group.create_dataset(dsname, data=np.array([np.nan]))
                else:
                    step_group.create_dataset(dsname, data=arr)
            except Exception:
                try:
                    step_group.attrs[dsname] = str(arr)
                except Exception:
                    pass
            if arr is not None and len(arr) > 0:
                plotfile = os.path.join(PLOTS_DIR, f"step_Chan{ch}_{pvname.replace(':','_')}.png")
                plot_and_save(arr, f"Step Chan{ch} {pvname}", plotfile)
                report_elements.append(Paragraph(f"Step Chan{ch} PV: {pvname}", styles['Normal']))
                report_elements.append(Image(plotfile, width=400, height=150))
                report_elements.append(Spacer(1,6))

    # Set to smooth ramp mode (opmode = 0)
    for ch in channels:
        safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_OpMode-SP"), 0)
    time.sleep(1)
    
    print("Waiting 10s to run Snapshot Buffer...")
    time.sleep(10)

    # Ramp to 12 Amps
    #for ch in channels:
    safe_caput(lab_replace(f"lab{{1}}Chan1:DAC_SetPt-SP"), 49.89)
    safe_caput(lab_replace(f"lab{{1}}Chan2:DAC_SetPt-SP"), 99.89)
    time.sleep(0.5)

    # snapshot for ramping
    print("Triggering ramp snapshot...")
    safe_caput(SS_TRIG_TEMPLATE1,1)
    #safe_caput(SS_TRIG_TEMPLATE2,1)
    safe_caput(SS_TRIG_TEMPLATE3,1)
    safe_caput(SS_TRIG_TEMPLATE4,1)
    #time.sleep(RAMP_WAIT)
    time.sleep(1)
    safe_caput(SS_TRIG_TEMPLATE2,1)
    time.sleep(14)

    # Pull ramp waveforms
    ramp_group = h5.require_group("ramp")
    for ch in channels:
        pv_templates = pv_template_list_for_channel(ch)
        for tmpl in pv_templates:
            pvname = lab_replace(tmpl)
            arr = read_pv_array(pvname)
            dsname = f"ramp/Chan{ch}/{pvname.replace(':','_')}"
            try:
                if arr is None:
                    ramp_group.create_dataset(dsname, data=np.array([np.nan]))
                else:
                    ramp_group.create_dataset(dsname, data=arr)
            except Exception:
                try:
                    ramp_group.attrs[dsname] = str(arr)
                except Exception:
                    pass
            if arr is not None and len(arr) > 0:
                plotfile = os.path.join(PLOTS_DIR, f"ramp_Chan{ch}_{pvname.replace(':','_')}.png")
                plot_and_save(arr, f"Ramp Chan{ch} {pvname}", plotfile)
                report_elements.append(Paragraph(f"Ramp Chan{ch} PV: {pvname}", styles['Normal']))
                report_elements.append(Image(plotfile, width=400, height=150))
                report_elements.append(Spacer(1,6))
                
    # ---- Steady State Capture ----
    
    print("Waiting 10s to run Snapshot Buffer...")
    time.sleep(10)
    
    # snapshot for ramping
    print("Triggering steady state snapshot...")
    safe_caput(SS_TRIG_TEMPLATE1,1)
    safe_caput(SS_TRIG_TEMPLATE2,1)
    safe_caput(SS_TRIG_TEMPLATE3,1)
    safe_caput(SS_TRIG_TEMPLATE4,1)
    time.sleep(RAMP_WAIT)
    
    # Pull ramp waveforms
    steady_state_group = h5.require_group("steady_state")
    for ch in channels:
        pv_templates = pv_template_list_for_channel(ch)
        for tmpl in pv_templates:
            pvname = lab_replace(tmpl)
            arr = read_pv_array(pvname)
            dsname = f"steady_state/Chan{ch}/{pvname.replace(':','_')}"
            try:
                if arr is None:
                    steady_state_group.create_dataset(dsname, data=np.array([np.nan]))
                else:
                    steady_state_group.create_dataset(dsname, data=arr)
            except Exception:
                try:
                    steady_state_group.attrs[dsname] = str(arr)
                except Exception:
                    pass
            if arr is not None and len(arr) > 0:
                plotfile = os.path.join(PLOTS_DIR, f"steady_state_Chan{ch}_{pvname.replace(':','_')}.png")
                plot_and_save(arr, f"Steady State Chan{ch} {pvname}", plotfile)
                report_elements.append(Paragraph(f"Steady State Chan{ch} PV: {pvname}", styles['Normal']))
                report_elements.append(Image(plotfile, width=400, height=150))
                report_elements.append(Spacer(1,6))

    # ---- FOFB test if Bandwidth-Mode is "Fast" ----
    #bandpv = lab_replace("lab{1}Bandwidth-Mode")
    bandval = caget('lab{1}Bandwidth-Mode',as_string=True)
    if bandval is not None and str(bandval).strip().lower() == "fast":
        report_elements.append(Paragraph("<b>FOFB test (Bandwidth-Mode == Fast)</b>", styles['Heading2']))
        print("Performing FOFB test because Bandwidth-Mode == Fast")
        # Caput IPaddr
        safe_caput(lab_replace(FOFB_IP_PV_TEMPLATE), int(0xA008E64))
        # Caput FastAddr for channels 0..3
        for ch_i, pvtemplate in enumerate(FOFB_FASTADDR_TEMPLATES):
            safe_caput(lab_replace(pvtemplate), ch_i)
        # Set DAC_OpMode-SP to 2 per script
        for ch in channels:
            safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_OpMode-SP"), 2)
        time.sleep(5)

        # Check that DAC-I etc are ~1.0
        ofc_table = [["PV", "Value", "Pass?"]]
        ofc_pass_all = True
        check_pvs = [f"lab{{1}}Chan{ch}:DAC-I" for ch in channels]
        # plus a couple of others from script
        check_pvs.append("lab{1}Chan2:USR:Reg-Wfm")
        check_pvs.append("lab{1}Chan2:USR:Error-Wfm")
        for tmpl in check_pvs:
            pvname = lab_replace(tmpl)
            val = safe_caget(pvname)
            status = "N/A"
            try:
                f = float(val)
                status = "PASS" if abs(f - 1.0) <= DAC_TOLERANCE else "FAIL"
            except Exception:
                # For waveforms we treat presence as pass/fail: if array length>0 -> PASS
                arr = read_pv_array(pvname)
                if arr is None:
                    status = "FAIL"
                else:
                    status = "PASS"
            ofc_table.append([pvname, str(val), status])
            if status != "PASS":
                ofc_pass_all = False
            print(f"{pvname}: {val} -> {status}")

        t_ofc = Table(ofc_table, colWidths=[300,150,80])
        t_ofc.setStyle([('GRID',(0,0),(-1,-1),0.5,colors.black),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)])
        report_elements.append(t_ofc)
        if ofc_pass_all:
            report_elements.append(Paragraph("<b>FOFB test: PASS</b>", styles['Normal']))
        else:
            report_elements.append(Paragraph("<b>FOFB test: FAIL</b>", styles['Normal']))
    else:
        report_elements.append(Paragraph("<b>FOFB test: SKIPPED (Bandwidth-Mode != Fast)</b>", styles['Normal']))
        print("Skipping FOFB test; Bandwidth-Mode not 'Fast'.")

    #Go back to Smooth Ramp mode
    for ch in channels:
        safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_OpMode-SP"), 0)
        
    # Ramp back to 0 Amps
    for ch in channels:
        safe_caput(lab_replace(f"lab{{1}}Chan{ch}:DAC_SetPt-SP"), 0.0)
    time.sleep(1)
    
    # Set Park High
    for pv in DIGOUT_PARK_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 1)
        
    # Turn OFF Supply Set On1 Low
    for pv in DIGOUT_ON1_TEMPLATES[:len(channels)]:
        safe_caput(lab_replace(pv), 0)


    # Finalize: write HDF5 and report
    h5.close()
    print("HDF5 file saved:", HDF5_FILENAME)
    print("Building PDF report:", REPORT_FILENAME)
    try:
        doc = SimpleDocTemplate(REPORT_FILENAME, pagesize=letter)
        doc.build(report_elements)
        print("Report written to", REPORT_FILENAME)
    except Exception as e:
        print("Error writing PDF:", e)
        traceback.print_exc()

    print("Script completed.")

if __name__ == "__main__":
    main()



 

 

