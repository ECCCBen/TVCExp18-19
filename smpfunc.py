"""
smpfunc.py

Functions to load and process smp data
J. King ECCC/CRD/CPS 2021
B. Montpetit ECCC/CRD/CPS 2024

"""
import numpy as np
import pandas as pd
import math
from scipy.signal import resample
from scipy.ndimage import gaussian_filter, interpolation
from snowmicropyn import Profile, loewe2012
import warnings

def load_smp_data(smp_path, window_size=5, overlap = 50, trim_dist = [0,10], noise_threshold = 0.01):
    """Load SMP data from pnt, apply QA, estaimte snot noise parameters
    Argrumnets: 
        smp_path: Path to the PNT file to be processed
        window_size: Processing window in mm 
        trim_dist: Trim away start or end of profile (in mm), useful for overpenetration.
        noise_threshold: Threadhold to apply noise compensation measure sin N
    Output:
        Pandas dataframe of force and shot noise parameters at resolution of noise_threshold/overlap
    """
    p = Profile.load(smp_path)

    # Remove samples below noise threshold and more than 100% change over 10 bins
    p.samples.force[p.samples.force <  noise_threshold] = np.nan
    outlier_bin_window = np.floor(10/p.spatial_resolution).astype(int) #hardcoded as 10 bins
    force_pct_change = np.abs(p.samples['force'].pct_change(outlier_bin_window))
    p.samples.force[force_pct_change>100] = np.nan

    # Interpolate across NaN values
    nans, x= nan_helper(p.samples.force)
    p.samples.force[nans]= np.interp(x(nans), x(~nans), p.samples.force[~nans])
    
    # Detect AS and SG (or SI) interfaces
    ground  = p.detect_ground()
    p.set_marker('ground', ground - trim_dist[1])
    
    surface  = p.detect_surface()
    p.set_marker('surface', surface + trim_dist[0])
    #print(surface)
    #p.set_marker('surface', 120)
    
    # This is a bandaid for issues in snowmicropyn
    # Error handling is broken for div 0 in lowe2012
    #try:
    smp_model = loewe2012.calc(p.samples_within_snowpack(), window=window_size, overlap = overlap)
    smp_model.columns = ['rel_height', 'force_median', 'lambda', 'f0', 'delta', 'l']   
    #except:
    #smp_model = np.nan
    
    return smp_model

def calc_density(shot_noise, coefs, return_df = False):
    """Calculate density from SMP shot noise params
    Argrumnets: 
        shot_noise: dataframe of smp properties from load_smp_data
        coefs: list of model coefficients
        return_df: bool flag to return dataframe
    Output:
        Pandas dataframe with density or np array of density 
    """
    density = np.round(coefs[0]+(coefs[1]*np.log(shot_noise.force_median))+ \
                (coefs[2]*np.log(shot_noise.force_median)*shot_noise.l)+ \
                coefs[3]*shot_noise.l, 1)
    
    #density = np.where(density<min_density, np.nan,density)
    if return_df:
        return shot_noise.assign(density = density)
    else:
        return density

def calc_ssa_loglog(shot_noise, coefs, return_df = False):
    """Calculate SSA from SMP shot noise params
    Argrumnets: 
        shot_noise: dataframe of smp properties from load_smp_data
        coefs: list of model coefficients
        return_df: bool flag to return dataframe
        min_density: ignore reference samples below a given density in kg m^3
    Output:
        Pandas dataframe with ssa or np array of ssa 
    """
    ssa = np.exp(coefs[0]+
                (coefs[1]*np.log(shot_noise.l))+  
                (coefs[2]*np.log(shot_noise.force_median)))
                   
    if return_df:
        return shot_noise.assign(ssa = ssa)
    else:
        return ssa
        
def calc_ssa(shot_noise, coefs, return_df = False):
    """Calculate SSA from SMP shot noise params
    Argrumnets: 
        shot_noise: dataframe of smp properties from load_smp_data
        coefs: list of model coefficients
        return_df: bool flag to return dataframe
        min_density: ignore reference samples below a given density in kg m^3
    Output:
        Pandas dataframe with ssa or np array of ssa 
    """
    ssa = np.round(coefs[0]+
                  (coefs[1]*np.log(shot_noise.l))+  
                  (coefs[2]*np.log(shot_noise.force_median)), 1)
                   
    if return_df:
        return shot_noise.assign(ssa = ssa)
    else:
        return ssa


def nan_helper(y):
    return np.isnan(y), lambda z: z.to_numpy().nonzero()[0]


def random_scaling(layer_num, max_change = 0.1, max_change_layer = 0.7):
    """Generate random numbers to manipulate either stretch (+) or erode
    Argrumnets: 
        layer_num: Number of random values to generate, ie. number of snowpack layers
        max_change: The maximum precentage that the total snowpack can be modified
        max_change_layer: The maximum precentage that an individual layer can be modified
    Output:
        A list of modifiers to erode or dilate snowpack layers based on the inputs
    """
    while True:
        layer_stretch = np.array([])
        layer_order = np.random.choice(layer_num, layer_num, replace=False)
        for layer in np.arange(0,len(layer_order)):
            layer_stretch =  np.append(layer_stretch, np.random.uniform(-max_change_layer,max_change_layer))
        if (np.abs(layer_stretch.sum()) <= max_change):
            break
    layer_order_sort = np.argsort(layer_order)
    return layer_stretch[layer_order_sort]

def scale_profile(scaling_guess, depth_array, value_array, l_resample = 40, h_resample = None):
    result_value = np.array([]); result_dist = np.array([])
    
    delta_h = np.diff(depth_array)[0] #This assumes its equal!
    if h_resample is None:
        h_resample = delta_h
    l_last = np.array(-h_resample)

    layer_thickness = l_resample + (scaling_guess * l_resample)
    new_total_thickness = sum(layer_thickness)
    depth_stretch= np.arange(0,new_total_thickness, h_resample)

    for l_idx in np.arange(len(layer_thickness)):
        ol_start = l_resample*l_idx
        old_end = ol_start + l_resample
        ol_start_idx = (np.abs(depth_array - ol_start)).argmin() # Do this incase mod(delta_h, l_resample)!=0 
        ol_end_idx = (np.abs(depth_array - old_end)).argmin()

        orig_dist = depth_array[ol_start_idx:ol_end_idx]
        orig_value = value_array[ol_start_idx:ol_end_idx]
        
        l_end = layer_thickness[0:l_idx+1].sum() - (layer_thickness[0:l_idx+1].sum() % h_resample)
        l_end_idx = (np.abs(depth_stretch - l_end)).argmin()
        l_start = l_last + h_resample
        l_start_idx = (np.abs(depth_stretch - l_start)).argmin()
        l_last = l_end
        
        if len(orig_value) > 2 :
            scaled_dist = depth_stretch[l_start_idx:l_end_idx+1]
            scaling_z = len(scaled_dist)/len(orig_dist)
            scaled_value = interpolation.zoom(orig_value,scaling_z)
            result_dist = np.append(result_dist,scaled_dist)
            result_value = np.append(result_value, scaled_value) 
    
    return result_dist, result_value

def calc_skill(result, window_size, drop_na = True):
    if drop_na:
        result.dropna(inplace=True)
    #result = result[result['count_samp']>=window_size] # Remove comparisons outside the profile
    result = result[~result['grain_type'].isin(['N', 'I'])] # Remove new snow and ice because we don't have enough samples
    
    r = np.corrcoef(result['mean_samp'],result['ref_val'])[1][0]
    rmse = np.sqrt(np.mean((result['mean_samp']-result['ref_val'])**2))
    return r, rmse

def extract_samples(a_height, a_value, b_height, window_size):
    #This throws silly warnings about an empty slice. We know this will happen from time to time...
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        extracted_samples =  pd.DataFrame({'count_samp': [np.count_nonzero(a_value[np.abs(a_height-height)<=window_size]) for height in b_height],
                            'mean_samp': [np.mean(a_value[np.abs(a_height-height)<=window_size]) for height in b_height], 
                            'median_samp': [np.median(a_value[np.abs(a_height-height)<=window_size]) for height in b_height],
                            'stdev_samp': [np.std(a_value[np.abs(a_height-height)<=window_size]) for height in b_height]})
    
    return extracted_samples


def eval_scaling(smp_dat, ref_dat, num_tests = 2000, layer_h = 50, 
                 max_stretch = 0.15, max_layer_stretch = 0.75, samp_h = 15):
    '''
        Generic method to test smp derived profile against reference data with scaling
        Input:
            smp_dat: dataframe of smp shot noise metrics
            ref_dat: dataframe of TVC reference data
            num_test: number of brute force iterations
            layer_h: height of layers for scaling (mm)
            max_stretch: max change in smp profile height (%)
            samp_h: 1/2 height of the reference measurements (mm)
            
        Output:
            scaling_meta: scaling statistics for best match
            scaling_result: result of best scaling match
    '''
    
    # Determine reference type 
    col_types = ['density', 'ssa']
    ref_iloc = [ref_dat.columns.get_loc(c) for c in col_types if c in ref_dat]
    ref_type = ref_dat.columns[ref_iloc][0]
    ref_dat.rename(columns={ref_type:'ref_val'}, inplace=True)
    smp_dat.rename(columns={ref_type:'smp_val'}, inplace=True) # TODO: Catch
    print("{}: Scaling SMP against {} reference with {} members".format(ref_dat['site'].iloc[0], ref_type, num_tests))

    # Generate scaling candidates
    min_len = np.amin([smp_dat['rel_height'].max(), ref_dat.height.max()])
    num_sections = np.ceil(min_len/layer_h).astype(int)
    random_tests = [random_scaling(x, max_stretch, max_layer_stretch) for x in np.repeat(num_sections, num_tests)]
    scaled_profiles = [scale_profile(test, smp_dat.rel_height.values, smp_dat.smp_val.values, layer_h) for test in random_tests]
    
    # Extract SMP data at refrence measurement heights
    compare_profiles = [extract_samples(dist, ref, ref_dat.rel_height.values, samp_h) for dist, ref in scaled_profiles]
    compare_profiles = [pd.concat([profile, ref_dat.reset_index(drop = True)], axis=1, sort=False) for profile in compare_profiles]
    retrieved_skill = [calc_skill(profile, samp_h) for profile in compare_profiles]
    retrieved_skill = pd.DataFrame(retrieved_skill,columns = ['r','rmse'])
    min_scaling_idx = retrieved_skill.sort_values(['r', 'rmse'], ascending=[False, True]).head(1).index.values
    
    # Summarize scaling evaluation
    scaling_meta = retrieved_skill.iloc[min_scaling_idx].reset_index()
    scaling_meta['ref_type'] = ref_type
    scaling_meta['scale_coeff'] = [random_tests[min_scaling_idx[0]]]
    scaling_meta['scale_per'] = sum(scaling_meta['scale_coeff'][0])
    scaling_meta['n_obs'] = len(ref_dat)
    scaling_meta['n_comp'] = len(compare_profiles[min_scaling_idx[0]])
    scaling_meta['n_tests'] = num_tests
    scaling_result = compare_profiles[min_scaling_idx[0]]
    
    return scaling_meta, scaling_result