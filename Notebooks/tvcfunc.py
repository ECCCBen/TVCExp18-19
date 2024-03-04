"""
tvcfunc.py

Functions used to process field data sets collected by ECCC at TVC

J. King ECCC/CRD/CPS 2021
M. Brady ECCC/CRD/CPS 2021
B. Montpetit ECCC/CRD/CPS 2024
 
"""

import os
from glob import glob
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from scipy import interpolate
from snowpit_datasheet_parser import SnowPitSheet

# Constants for file type patterns
SMP_PATTERN = "SMP*"
PNT_PATTERN = "*.pnt"
PIT_PATTERN = "PIT*"
SSA_PATTERN = "SSA*"
MP_PATTERN = "MP_*"

def calc_rmse(x):
    return np.sqrt(np.mean((x['smp_val'] - x['ref_val'])**2))

def gen_site_meta(base_folder):
    '''
    Matches expected files to sites
    '''
    site_meta = pd.DataFrame({'site': [],
                             'pnt_files': [],
                             'smp_meta': [],
                             'pit_files': [],
                             'ssa_files': [],
                             'mp_files': []})
    pnt_files = []; ssa_files = []; pit_files = []; mp_files = []; smp_files = []
    for root,_,_ in os.walk(base_folder):
        pnt_files.extend(glob(os.path.join(root,PNT_PATTERN)))
        smp_files.extend(glob(os.path.join(root,SMP_PATTERN)))
        ssa_files.extend(glob(os.path.join(root,SSA_PATTERN)))
        pit_files.extend(glob(os.path.join(root,PIT_PATTERN)))
        mp_files.extend(glob(os.path.join(root,MP_PATTERN)))
              
    site_names = next(os.walk(base_folder))[1]
    for site in site_names:
        match_pnt = [s for s in pnt_files if site in s]
        match_smp = [s for s in smp_files if site in s]
        match_ssa = [s for s in ssa_files if site in s]
        match_pit = [s for s in pit_files if site in s]
        match_mp = [s for s in mp_files if site in s]

        site_meta = pd.concat([site_meta,pd.DataFrame({'site': [site],
                                       'pnt_files': [match_pnt],
                                       'smp_meta': [match_smp],
                                       'pit_files': [match_pit],
                                       'ssa_files': [match_ssa],
                                       'mp_files': [match_mp]})],ignore_index=True)
        
    return(site_meta)

def load_ref_rho(pit_path):
    '''
    Loads in TVC data to create standard refernce data for SMP calibration
    '''
    snow_pit = SnowPitSheet(pit_path)
    
    # Create density reference dataframe
    rho_mid_height = snow_pit.data.density['HeightAboveGround_Bot[cm]'] + \
                     ((snow_pit.data.density['HeightAboveGround_Top[cm]'] - \
                     snow_pit.data.density['HeightAboveGround_Bot[cm]'])/2)
    rho_rel_height = (snow_pit.meta['total_depth'] - rho_mid_height)*10
    
    ref_rho_df = pd.DataFrame()
    ref_rho_df = ref_rho_df.assign(height=rho_mid_height*10)
    ref_rho_df = ref_rho_df.assign(rel_height=rho_rel_height)
    
    # Average the A/B desnity profiles if they exist
    if not all(np.isnan(snow_pit.data.density['DensityProfile_B[kg/m^3]'])):
        ref_rho_df = ref_rho_df.assign(density = snow_pit.data.density[['DensityProfile_A[kg/m^3]', \
                                                             'DensityProfile_B[kg/m^3]']].mean(axis=1))    
    else:
        ref_rho_df = ref_rho_df.assign(density = snow_pit.data.density['DensityProfile_A[kg/m^3]'])
                                                   
    ref_rho_df.dropna(how='all', subset=['density'], inplace = True)
    ref_rho_df = ref_rho_df.assign(grain_type=None)
    
    # Assign a grain type to each desnity sample
    gtype_density = []
    strat = snow_pit.data.stratigraphy.iloc[::2, :]
    strat.dropna(how='all', inplace = True)
    strat.drop(strat[strat.GrainType == 'C'].index, inplace = True)
    
    for i, row in ref_rho_df.iterrows():
        # Sometimes the snow pit is shorter than the density profile or if the top layer is a crust.
        if (row['height']> strat['HeightAboveGround_Top[cm]'].max()*10):
            gtype_density.append(strat.iloc[0].GrainType)
        else:
            gtype_density.append(strat[row['height'] <= strat['HeightAboveGround_Top[cm]']*10].iloc[-1].GrainType)
    ref_rho_df = ref_rho_df.assign(grain_type=gtype_density)
    
    return ref_rho_df

def load_ref_temperature(pit_path):
    snow_pit = SnowPitSheet(pit_path)
    temperature_height = snow_pit.data.temperature['HeightAboveGround[cm]'].values*10
    temperature_rel_height = (snow_pit.meta['total_depth']*10 - temperature_height)
    temperature_k = snow_pit.data.temperature['Temperature[C]'].values + 273.15
    ref_temperature_df = pd.DataFrame()
    ref_temperature_df = ref_temperature_df.assign(height=temperature_height)
    ref_temperature_df = ref_temperature_df.assign(rel_height=temperature_rel_height)
    ref_temperature_df = ref_temperature_df.assign(temperature_k=temperature_k)
    ref_temperature_df.dropna(how='all', subset=['temperature_k'], inplace = True)
    ref_temperature_df['type'] = 'snow'
    ref_temperature_df.loc[ref_temperature_df['height']<0, 'type'] = 'soil'
    ref_temperature_df.loc[ref_temperature_df['height']==0, 'type'] = 'sg'
    ref_temperature_df.loc[ref_temperature_df['rel_height']<0, 'type'] = 'air'
    ref_temperature_df.loc[ref_temperature_df['rel_height']==0, 'type'] = 'as'
    return ref_temperature_df

def load_ref_ssa(ssa_path, pit_path):
    '''
    Loads in TVC data to create standard SSA data for SMP calibration
    
    '''
    snow_pit = SnowPitSheet(pit_path)
    ssa_data =  pd.read_csv(ssa_path)
    ssa_mid_height = (ssa_data['Bottom'] + ((ssa_data['Top'] - \
                      ssa_data['Bottom'])/2))
    ssa_rel_height = (snow_pit.meta['total_depth'] - ssa_mid_height)*10
    
    ref_ssa_df = pd.DataFrame()
    ref_ssa_df = ref_ssa_df.assign(height=ssa_mid_height*10)
    ref_ssa_df = ref_ssa_df.assign(rel_height=ssa_rel_height)
    ref_ssa_df = ref_ssa_df.assign(ssa=ssa_data['SSA'])
    ref_ssa_df.dropna(how='all', subset=['ssa'], inplace = True)
    
    gtype_ssa = []
    strat = snow_pit.data.stratigraphy.iloc[::2, :]
    strat.dropna(how='all', inplace = True)
    strat.drop(strat[strat.GrainType == 'C'].index, inplace = True)
    
    for i, row in ref_ssa_df.iterrows():
        # Sometimes the snow pit is shorter than the SSA profile. Assign the top layer if so for grain type
        if (row['height']> strat['HeightAboveGround_Top[cm]'].max()*10):
            gtype_ssa.append(strat.iloc[0].GrainType)
        else:
            gtype_ssa.append(strat[row['height'] <= strat['HeightAboveGround_Top[cm]']*10].iloc[-1].GrainType)
    ref_ssa_df = ref_ssa_df.assign(grain_type=gtype_ssa)
    
    return ref_ssa_df

def load_smp_meta(base_folder, site_name=None):
    '''
    Loads SMP meta files created during TVCSnow19
    '''
    files = []
    smp_list = []

    for dir,_,_ in os.walk(base_folder):
        files.extend(glob(os.path.join(dir,SMP_PATTERN)))
    
    if (site_name is not None):
        files = [s for s in files if site_name in s]
    
    for filename in files:
        smp_df = pd.read_csv(filename)
        smp_df['site'] = filename.split('\\')[-2]
        smp_list.append(smp_df)
        
    smp_meta_df = pd.concat(smp_list, axis=0, ignore_index=True)
    smp_meta_df.columns  = ['position', 'file', 'probe', 'pen', 'notes', 'site']
    smp_meta_df['smp_path'] = np.nan 
    smp_meta_df['pit_path'] = np.nan  
    smp_meta_df['ssa_path'] = np.nan
    smp_meta_df.replace(['-99999', -99999], np.nan, inplace = True)
    smp_meta_df['file'] = smp_meta_df['file'].astype('Int64')
    
    return smp_meta_df

def match_smp_file(base_folder, smp_meta):
    pnt_files = []
    ssa_files = []
    pit_files = []
    
    for dir,_,_ in os.walk(base_folder):
        pnt_files.extend(glob(os.path.join(dir,PNT_PATTERN)))
        ssa_files.extend(glob(os.path.join(dir,SSA_PATTERN)))
        pit_files.extend(glob(os.path.join(dir,PIT_PATTERN)))
    
    for idx, profile in smp_meta.iterrows():
        smp_match = [file for file in pnt_files if str(profile.file) in file]
        if len(smp_match)==1:
            smp_meta.iloc[idx, smp_meta.columns.get_loc('smp_path')] = smp_match[0]
            
        if ('SSA' in profile['position']) | ('RHO' in profile['position']):
            pit_match = [file for file in pit_files if str(profile.site) in file]
            ssa_match = [file for file in ssa_files if str(profile.site) in file]

            smp_meta.iloc[idx, smp_meta.columns.get_loc('pit_path')] = pit_match[0]
            smp_meta.iloc[idx, smp_meta.columns.get_loc('ssa_path')] = ssa_match[0]  
    
    if (any(smp_meta['smp_path'].isnull())):
        print('match_smp_file: SMP meta missing link to PNT file(s)')
        

    return smp_meta


def quicklook(smp_rho, smp_ssa, ref_rho, ref_ssa):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, sharey=True,  figsize=(10, 6))
    ax1.invert_yaxis()
    # Plot force and density profiles
    for profile in smp_rho:
        ax1.plot(np.log(profile['force_median']), profile['rel_height'], color = 'darkgrey', zorder=0)
        ax2.plot(profile['density'], profile['rel_height'], color = 'darkgrey', zorder=0)
    ax2.scatter(ref_rho['density'], ref_rho['rel_height'], color = 'r', zorder=1)
    
    for profile in smp_ssa:
        ax3.plot(profile['ssa'], profile['rel_height'], color = 'darkgrey')
    ax3.scatter(ref_ssa['ssa'], ref_ssa['rel_height'], color = 'r', label = 'Ref.')
    
    ax2.set_title('SMP quickplot for ' + ref_ssa['site'].iloc[0])
    ax1.set_xlabel('Pen. Force [ln(N)]')
    ax1.set_ylabel('Pen. Distance [mm]')
    ax2.set_xlabel('Snow Density [kg m$^{-3}$]')
    ax3.set_xlabel('SSA [m$^{2}$ kg]')

    return fig

def rtc_check_mp(mp_time):
    '''
    Check magnaprobe timestamps to look for real time clock failures
    Input:
        mp_time: pandas series or list of datetime64 timestamps

    '''
    time_fix = []; rtc_fail = []

    for time in mp_time:
        time_df = pd.to_datetime(time)
        time_fix.append(time_df)
        if time_df.year < 2018:
            rtc_fail.append(True)
        else:
            rtc_fail.append(False)
        
    return time_fix, rtc_fail

def interp_profile(data, var, res = 10):
    height_range = data['height'].max() - data['height'].min()
    # We try to approximate res as best possible where the range 
    # might produce a remainder otherwise
    height_interp = np.linspace(data['height'].min(), 
                                data['height'].max(), 
                                np.ceil(height_range/res).astype(int))
    
    func_intep = interpolate.interp1d(data['height'], data[var])
    var_intep = func_intep(height_interp)
    var_out = pd.DataFrame({'height': height_interp, var: var_intep})
    return var_out

# TODO: handle out nan values better than fill
def sample_profile(data, var, bins):
    var_bins = pd.cut(data['height'], bins)
    layer_var = data.groupby(var_bins)[var].agg(['count', 'mean']).ffill().bfill()
    return layer_var

# TODO: add somthing smart instead of dumping coherent layers
def standardize_pit(pit, ssa, dens, temp):
    '''
    Generate standardized snow pit representations from the reference data
    Input:
        pit: ECCC parsed snow pit dataframe
        ssa: ECCC IceCube SSA dataframe
        dens: ECCC cutter density dataframe
        temp: ECCC digitial temperature dataframe
    Output:
        sp_out: Standardized snow pit dataframe
    '''
    strat = pit.data.stratigraphy.iloc[::2, :]
    strat.dropna(how='all', subset=['HeightAboveGround_Top[cm]'], inplace = True)
    strat = strat.loc[strat['HeightAboveGround_Top[cm]'] - strat['HeightAboveGround_Bot[cm]'] > 1]
    
    # Generate boundaries for each layer as an array
    layer_bins = np.flip(np.round(np.append(strat['HeightAboveGround_Top[cm]'].values*10, 0).tolist(),3))
    intep_ssa = interp_profile(ssa, 'ssa', 10)
    intep_dens = interp_profile(dens, 'density', 10)
    intep_temp = interp_profile(temp, 'temperature_k', 10)
    
    layer_ssa = sample_profile(intep_ssa, 'ssa', layer_bins)
    layer_dens = sample_profile(intep_dens, 'density', layer_bins)
    layer_temp = sample_profile(intep_temp, 'temperature_k', layer_bins)
    
    sp_out = pd.DataFrame({'l_height_top': layer_bins[1:]/1000,
                            'thickness': np.diff(layer_bins)/1000, # in m 
                            'grain_type': np.flip(strat['GrainType'].values),
                            'density': layer_dens['mean'].values,
                            'ssa': layer_ssa['mean'].values,
                            'temperature': layer_temp['mean'].values}).iloc[::-1].reset_index(drop=True)
    
    return sp_out

