"""
radarfunc.py

Common functions to generate snowpit input files for SMRT (Picard et al., 2018)
J. King ECCC/CRD/CPS 2021
B. Montpetit ECCC/CRD/CPS 2024

"""

import numpy as np
import pandas as pd
import constants

# SMRT imports
from smrt import make_snowpack
from smrt.substrate.reflector_backscatter import make_reflector


# Radar helpers
def to_dB(val):
    """
    Convert linear units to decibel
    """
    return 10*np.log10(val)

def to_lin(val):
    """
    Convert decibel units to linear
    """
    return 10**((val)/10)


# TODO: paramterize LW
def pit_to_smrt(pit, phi_corr = 1, return_df = False):
    pit['vol_frac'] = pit['density']/constants.RHO_ICE
    pit['d0'] = 6/(constants.RHO_ICE*pit['ssa'])
    pit['p_ex'] = phi_corr * 2/3 * pit['d0'] * (1-pit['vol_frac'])
    pit_smrt = make_snowpack(thickness=pit['thickness'].values,
                              microstructure_model="exponential",
                              density=pit['density'].values,
                              temperature=pit['temperature'].values,
                              liquid_water=0,
                              corr_length=pit['p_ex'].values)
    if return_df:
        return pit_smrt, pit
    else: 
        return pit_smrt


def syn_to_smrt(pit, phi_corr = 1, bg=None):
    pit_smrt = make_snowpack(thickness=pit['thickness'].values,
                              microstructure_model="exponential",
                              density=pit['density'].values,
                              temperature=pit['temperature'].values,
                              liquid_water=0,
                              corr_length=pit['corr_length'].values*phi_corr)
    pit_smrt.substrate = bg
    return pit_smrt
    
    
def create_bg(date_ts, site_name, inc, temp, spec=0.5, date_window = 15, power_idx = 1.25):
    rs2_data = pd.read_pickle("../Output/Data/rs2_stats.pkl")
    rs2_data = rs2_data.dropna(subset = ['VV'])

    rs2_lim = rs2_data.loc[(rs2_data['timestamp'] < (date_ts + np.timedelta64(date_window,'D'))) & \
                       (rs2_data['timestamp'] > (date_ts - np.timedelta64(date_window,'D')))]
    rs2_lim = rs2_lim.loc[rs2_lim['site'] == site_name[0:2]]

    rs2_samp = rs2_lim.sample()
    vv_obs = to_dB(rs2_samp['VV'].values)
    hh_obs = to_dB(rs2_samp['VV'].values)
    inc_obs = rs2_samp['inc'].values
    
    vv_norm = (vv_obs * np.cos(np.radians(inc_obs))**power_idx) / (np.cos(np.radians(inc))**power_idx)
    hh_norm = (hh_obs * np.cos(np.radians(inc_obs))**power_idx) / (np.cos(np.radians(inc))**power_idx)
    
    background = make_reflector(temperature=temp, 
                                specular_reflection=0.75,
                                backscattering_coefficient={'VV': to_lin(vv_norm), 
                                                            'HH': to_lin(hh_norm)})
    return background

