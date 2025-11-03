import os
import glob
import re
import struct
from pathlib import Path
from collections import defaultdict
from pynq.pl_server import Device, RemoteDevice
from pynq.remote import xrfclk_pb2, xrfclk_pb2_grpc

_Config = defaultdict(dict)
_Devices = defaultdict(dict)

def _write_LMK_regs(reg_vals, device):
    request = xrfclk_pb2.WriteLmkRegsRequest(reg_vals=reg_vals)
    try:
        device._stub['xrfclk'].write_lmk_regs(request)
    except Exception as e:
        raise RuntimeError(f"Failed to write LMK registers: {e}")
        
def _write_LMX_regs(reg_vals, device):
    request = xrfclk_pb2.WriteLmxRegsRequest(reg_vals=reg_vals)
    try:
        device._stub['xrfclk'].write_lmx_regs(request)
    except Exception as e:
        raise RuntimeError(f"Failed to write LMX registers: {e}")

def _set_LMK_regs(lmk_freq, device):
    if lmk_freq not in _Config[_Devices[device]['lmk']]:
        print(_Config)
        raise RuntimeError(f"LMK frequency {lmk_freq} MHz not supported for this device.")
    else:
        reg_vals = _Config[_Devices[device]['lmk']][lmk_freq]
        _write_LMK_regs(reg_vals, device)

def _set_LMX_regs(lmx_freq, device):
    if lmx_freq not in _Config[_Devices[device]['lmx']]:
        raise RuntimeError(f"LMX frequency {lmx_freq} MHz not supported for this device.")
    else:
        reg_vals = _Config[_Devices[device]['lmx']][lmx_freq]
        _write_LMX_regs(reg_vals, device)

def set_ref_clks(lmk_freq=122.88, lmx_freq=409.6, device=None):
    try:
        if not device:
            device = Device.active_device
    except:
        raise RuntimeError("No remote device found. Either use the PYNQ_REMOTE_DEVICE environment variable or pass device explicitly.")
    if type(device) != RemoteDevice:
        raise RuntimeError("This function is only supported on remote devices.")
    if not _Devices:
        _find_devices(device)
    if not _Config:
        _read_tics_output()
        
    _set_LMK_regs(lmk_freq, device)
    _set_LMX_regs(lmx_freq, device)
    
def _find_devices(device):
    device._stub['xrfclk'] = xrfclk_pb2_grpc.XrfclkStub(device.client.channel)
    response = device._stub['xrfclk'].find_devices(xrfclk_pb2.FindDevicesRequest())
    _Devices[device]['lmk'] = response.lmk_device
    _Devices[device]['lmx'] = response.lmx_device
        
    
def _read_tics_output(config_dir=None):
    """Read all the TICS register values from all the txt files.
    
    Fill a single dictionary with dictionaries for each chip.
    Can store multiple frequencies per chip.

    Reading all the configurations from the specified directory, current 
    working directory, or module directory (in that priority order).
    File format: `CHIPNAME_frequency.txt`.

    Parameters
    ----------
    config_dir : str, optional
        Path to directory containing TICS configuration files.
        If None, searches current working directory first, then module directory.

    Raises
    ------
    RuntimeError
        If specified config_dir doesn't exist or no .txt files found in search paths.

    """
    if config_dir is not None:
        if not os.path.exists(config_dir):
            raise RuntimeError(f"Specified config directory does not exist: {config_dir}")
        search_paths = [config_dir]
    else:
        # No path specified - search current dir first, then module dir
        cwd = os.getcwd()
        module_dir = os.path.dirname(os.path.realpath(__file__))
        search_paths = [cwd, module_dir] if cwd != module_dir else [cwd]
    
    # Try each search path until we find .txt files
    all_txt = []
    used_path = None
    for dir_path in search_paths:
        all_txt = glob.glob(os.path.join(dir_path, '*.txt'))
        if all_txt:
            used_path = dir_path
            break
    
    if not all_txt:
        search_str = f"'{config_dir}'" if config_dir else f"current directory or module directory"
        raise RuntimeError(f"No tics configuration files found in {search_str}")
    
    for s in all_txt:
        chip, freq = os.path.splitext(os.path.basename(s.lower()))[0].split('_')
        
        with open(s, 'r') as f:
            lines = [l.rstrip("\n") for l in f]
                
            registers = []
            for i in lines:
                m = re.search('[\t]*(0x[0-9A-F]*)', i)
                if m:
                    registers.append(int(m.group(1), 16))
                    
        _Config[chip][float(freq)] = registers