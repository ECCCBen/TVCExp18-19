"""
constants.py

Constants and configs used in TVC analysis

J. King ECCC/CRD/CPS 2021
B. Montpetit ECCC/CRD/CPS 2024

"""
# Seeding
RANDOM_SEED = 2021

# Graphical constants
AXIS_LABEL_SIZE = 14

# SMP analysis constants
RHO_ICE = 917
WINDOW_SIZE = 5  # SMP analysis window in mm
CUTTER_SIZE = 15  # Half height of the density cutter in mm
KING_COEFF = [312.54, 50.27, -50.26, -85.38] # from King 2020
CALONNE_COEFF = [0.57, -18.56, -3.66] # from C 2020
L_HEIGHT = 50 # Arbitrary layer height in mm
GRID_PLOT_RES = 200 # resampled resolution in vertical bins
INTERP_BINS_PIT = 10 # resampled resolution in mm

# Site analysis constants
SITE_BUFFER = 50 #in m
DATE_WINDOW = 7 # in days
SS_NAMES = ['SC','SD', 'SM', 'SO', 'ST', 'SV']
TVC01 = ['RS01', 'RS02', 'RS03', 'RS04', 'RS05', 'RS06', 'RS07', 'RS08',
         'RS09', 'RS10', 'RS11', 'RS12', 'RS13', 'RS14', 'RS15', 'SC01',
         'SD01', 'SM01', 'SO01', 'SR01', 'ST01', 'SV01']
TVC02 = ['RS16','RS17', 'RS18', 'RS19', 'RS20', 'RS21', 'RS22', 'RS23', 
         'RS24','RS25', 'RS26', 'RS27', 'RS28', 'RS29', 'RS30', 'RS31',
         'SC02','SD02', 'SM02', 'SO02', 'ST02', 'SV02']
TVC03 = ['RS32','RS33', 'RS34', 'RS35', 'RS36', 'RS37', 'RS38', 'RS39', 
         'RS40','RS41', 'RS42', 'RS43', 'RS44', 'RS45', 'RS46', 'RS47', 
         'RS48','RS49', 'RS50', 'RS51', 'RS52', 'RS53', 'RS54', 'RS55',
         'SC03','SD03', 'SM03', 'SO03', 'SR03', 'ST03', 'SV03']
VEG_CLASS = ['Tree', 'Tall Shrub', 'Riparian Shrub', 'Dwarf Shrub', 
             'Tussock', 'Lichen', 'Water']

# EPSG codes for TVC
CRS_WGS84 = 'epsg:4326' # WGS84
CRS_UTM8N = 'epsg:32608' # Local UTM grid

# File type patterns
SLC_PATTERN = "*slc0.tif"
INC_PATTERN = "*inc.tif"

# Radar constants
TVC_INC_RANGE = [20,50]
PIXEL_AREA = 4 #in m^2

# Relative file paths
VEG_TYPE_FILE = r'../Data/vegetation_map_TVC_2019.tif'
VEG_HEIGHT_FILE = r'../Data/TVC_ALS_201808_VegetationHeight_Mean.tif'
DTM_ELV_FILE = r'../Data/TVC_ALS_201808_DTM.tif'