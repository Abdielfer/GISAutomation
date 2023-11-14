import os, ntpath
import glob
import pathlib
import shutil
from time import strftime
from typing import Tuple, List, overload
import pandas as pd
import numpy as np
from numpy import linspace
import matplotlib.pyplot as plt
from scipy.stats.kde import gaussian_kde
import torch
import rasterio as rio
from rasterio.plot import show_hist
from rasterio.enums import Resampling
from datetime import datetime
from whitebox.whitebox_tools import WhiteboxTools, default_callback
import whitebox_workflows as wbw   
from torchgeo.datasets.utils import download_url
from osgeo import gdal,ogr, osr
from osgeo import gdal_array
from osgeo.gdalconst import *
import geopandas as gpd
gdal.UseExceptions()

import pcraster as pcr
from pcraster import *

from omegaconf import DictConfig, OmegaConf
from hydra.utils import instantiate

### General applications ##
class timeit(): 
    '''
    to compute execution time do:
    with timeit():
         your code, e.g., 
    '''
    def __enter__(self):
        self.tic = datetime.now()
    def __exit__(self, *args, **kwargs):
        print('runtime: {}'.format(datetime.now() - self.tic))

def makeNameByTime():
    name = strftime("%y%m%d%H%M")
    return name

### Configurations And file management
def importConfig():
    with open('./config.txt') as f:
        content = f.readlines()
    # print(content)    
    return content

def getLocalPath():
    return os.getcwd()

def makePath(str1,str2):
    return os.path.join(str1,str2)

def ensureDirectory(pathToCheck:os.path)->os.path:
    if not os.path.isdir(pathToCheck): 
        os.mkdir(pathToCheck)
        print(f"Confirmed directory at: {pathToCheck} ")
    return pathToCheck

def relocateFile(inputFilePath, outputFilePath):
    '''
    NOTE: @outputFilePath must contain the complete filename
    Sintax:
     @shutil.move("path/to/current/file.foo", "path/to/new/destination/for/file.foo")
    '''
    shutil.move(inputFilePath, outputFilePath)
    return True

def makeFileCopy(inputFilePath, outputFilePath):
    try:
        shutil.copy(inputFilePath, outputFilePath)
        return outputFilePath
    except shutil.SameFileError:
        print("Source and destination represents the same file.")
    except PermissionError:
        print("Permission denied.")
    except:
        print("Error occurred while copying file.")

def removeFile(filePath):
    try:
        os.remove(filePath)
        return True
    except OSError as error:
        print(error)
        print("File path can not be removed")
        return False

def removeFilesBySubstring(parentPath,subStr:str=''):
    list = listALLFilesInDirBySubstring_fullPath(parentPath,subStr)
    for i in list:
        removeFile(i)

def createTransitFolder(parent_dir_path, folderName:str = 'TransitDir'):
    path = os.path.join(parent_dir_path, folderName)
    ensureDirectory(path)
    return path

def clearTransitFolderContent(path:str, filetype = '/*'):
    '''
    NOTE: This well clear dir without removing the parent dir itself. 
    We can replace '*' for an specific condition ei. '.tif' for specific fileType deletion if needed. 
    @Arguments:
    @path: Parent directory path
    @filetype: file type to delete. @default ='/*' delete all files. 
    '''
    files = glob.glob(path + filetype)
    for f in files:
        os.remove(f)
    return True

def extractNamesListFromFullPathList(pathlist, initialValues:list=[])-> list:
    '''
    From the list of path extract the names, then split by underscore 
    character and returns a list of the last substring from each element in the input.
    '''
    if initialValues:
        listOfNames = initialValues
    else:
        listOfNames =[]
    for path in pathlist:
        _,tifName,_ = get_parenPath_name_ext(path)
        listOfNames.append(tifName.split("_")[-1])
    return listOfNames

def listFreeFilesInDirByExt(cwd:str, ext = '.tif'):
    '''
    @ext = *.tif by default.
    NOTE:  THIS function list only files that are directly into <cwd> path. 
    '''
    cwd = os.path.abspath(cwd)
    # print(f"Current working directory: {cwd}")
    file_list = []
    for (root, dirs, file) in os.walk(cwd):
        for f in file:
            # print(f"File: {f}")
            _,_,extent = get_parenPath_name_ext(f)
            if extent == ext:
                file_list.append(f)
    return file_list

def listFreeFilesInDirByExt_fullPath(cwd:str, ext = '.csv') -> list:
    '''
    @ext = *.csv by default.
    NOTE:  THIS function list only files that are directly into <cwd> path. 
    '''
    cwd = os.path.abspath(cwd)
    # print(f"Current working directory: {cwd}")
    file_list = []
    for (root,_, file) in os.walk(cwd, followlinks=True):
        for f in file:
            # print(f"Current f: {f}")
            _,extent = splitFilenameAndExtention(f)
            # print(f"Current extent: {extent}")
            if ext == extent:
                file_list.append(os.path.join(root,f))
    return file_list

def listFreeFilesInDirBySubstring_fullPath(cwd:str, substring = '') -> list:
    '''
    @substring: substring to be verify onto the file name. 
    NOTE:  THIS function list only files that are directly into <cwd> path. 
    '''
    cwd = os.path.abspath(cwd)
    # print(f"Current working directory: {cwd}")
    file_list = []
    for (root,_, file) in os.walk(cwd, followlinks=True):
        for f in file:
            if substring.lower() in f.lower():
                file_list.append(os.path.join(root,f))
    return file_list

def listALLFilesInDirByExt(cwd, ext = '.csv'):
    '''
    @ext = *.csv by default.
    NOTE:  THIS function list ALL files that are directly into <cwd> path and children folders. 
    '''
    fullList: list = []
    for (root, _, _) in os.walk(cwd):
         fullList.extend(listFreeFilesInDirByExt(root, ext)) 
    return fullList

def listALLFilesInDirByExt_fullPath(cwd, ext = '.csv'):
    '''
    @ext: NOTE <ext> must contain the "." ex: '.csv'; '.tif'; etc...
    NOTE:  THIS function list ALL files that are directly into <cwd> path and children folders. 
    '''
    fullList = []
    for (root, _, _) in os.walk(cwd):
        # print(f"Roots {root}")
        localList = listFreeFilesInDirByExt_fullPath(root, ext)
        # print(f"Local List len :-->> {len(localList)}")
        fullList.extend(localList) 
    return fullList

def listALLFilesInDirBySubstring_fullPath(cwd, substring = '.csv'):
    '''
    @substring: substring to be verify onto the file name.    NOTE:  THIS function list ALL files that are directly into <cwd> path and children folders. 
    '''
    fullList = []
    for (root, _, _) in os.walk(cwd):
        # print(f"Roots {root}")
        localList = listFreeFilesInDirBySubstring_fullPath(root, substring)
        # print(f"Local List len :-->> {len(localList)}")
        fullList.extend(localList) 
    return fullList

def createListFromCSV(csv_file_location, delim:str =','):  
    '''
    @return: list from a <csv_file_location>.
    Argument:
    @csv_file_location: full path file location and name.
    '''       
    df = pd.read_csv(csv_file_location, index_col= None, header=None, delimiter=delim)
    out = []
    for i in range(0,df.shape[0]):
        out.append(df.iloc[i,:].tolist()[0])     
    return out

def createListFromCSVColumn(csv_file_location, col_idx, delim:str =','):  
    '''
    @return: list from <col_id> in <csv_file_location>.
    Argument:
    @csv_file_location: full path file location and name.
    @col_idx : number or str(name)of the desired collumn to extrac info from (Consider index 0 <default> for the first column, if no names are assigned in csv header.)
    @delim: Delimiter to pass to pd.read_csv() function. Default = ','.
    '''       
    x=[]
    df = pd.read_csv(csv_file_location,index_col=None, delimiter = delim)
    if isinstance(col_idx,str):  
        colIndex = df.columns.get_loc(col_idx)
    elif isinstance(col_idx,int): 
        colIndex = col_idx
    fin = df.shape[0] ## rows count.
    for i in range(0,fin): 
        x.append(df.iloc[i,colIndex])
    return x
 
def createListFromExelColumn(excell_file_location,Sheet_id:str, col_idx:str):  
    '''
    @return: list from <col_id> in <excell_file_location>.
    Argument:
    @excell_file_location: full path file location and name.
    @col_id : number of the desired collumn to extrac info from (Consider index 0 for the first column)
    '''       
    x=[]
    df = pd.ExcelFile(excell_file_location).parse(Sheet_id)
    for i in df[col_idx]:
        x.append(i)
    return x

def splitFilenameAndExtention(file_path):
    '''
    pathlib.Path Options: 
    '''
    fpath = pathlib.Path(file_path)
    extention = fpath.suffix
    name = fpath.stem
    return name, extention 

def createShpList(parentDir)-> os.path:
    listOfPath = listALLFilesInDirByExt_fullPath(parentDir,ext='.shp')
    OutCSVPath = os.path.join(parentDir,'listOfShpFiles.csv')
    createCSVFromList(OutCSVPath,listOfPath)
    return OutCSVPath 

def remove_duplicates_ordered(input_list)->list:
    seen = set()
    return [x for x in input_list if not (x in seen or seen.add(x))]

def replaceExtention(inPath,newExt: str)->os.path :
    '''
    Just remember to add the poin to the new ext -> '.map'
    '''
    dir,fileName = ntpath.split(inPath)
    _,actualExt = ntpath.splitext(fileName)
    return os.path.join(dir,ntpath.basename(inPath).replace(actualExt,newExt))

def get_parenPath_name_ext(filePath):
    '''
    Ex: user/folther/file.txt
    parentPath = pathlib.PurePath('/src/goo/scripts/main.py').parent 
    parentPath => '/src/goo/scripts/'
    parentPath: can be instantiated.
         ex: parentPath[0] => '/src/goo/scripts/'; parentPath[1] => '/src/goo/', etc...
    '''
    parentPath = pathlib.PurePath(filePath).parent
    name,ext = splitFilenameAndExtention(filePath)
    return parentPath, name, ext
  
def addSubstringToName(path, subStr: str, destinyPath = None) -> os.path:
    '''
    @path: Path to the raster to read. 
    @subStr:  String o add at the end of the origial name
    @destinyPath (default = None)
    '''
    parentPath,name,ext= get_parenPath_name_ext(path)
    if destinyPath != None: 
        return os.path.join(destinyPath,(name+subStr+ext))
    else: 
        return os.path.join(parentPath,(name+subStr+ ext))

def replaceName_KeepPathAndExt(path, newName: str) -> os.path:
    '''
    @path: Path to the raster to read. 
    @subStr:  String o add at the end of the origial name
    @destinyPath (default = None)
    '''
    parentPath,_,ext= get_parenPath_name_ext(path)
    return os.path.join(parentPath,(newName+ext))
    
def createCSVFromList(pathToSave: os.path, listData:list):
    '''
    This function create a *.csv file with one line per <lstData> element. 
    @pathToSave: path of *.csv file to be writed with name and extention.
    @listData: list to be writed. 
    '''
    parentPath,name,_ = get_parenPath_name_ext(pathToSave)
    textPath = makePath(parentPath,(name+'.txt'))
    with open(textPath, 'w') as output:
        for line in listData:
            output.write(str(line) + '\n')
    read_file = pd.read_csv (textPath)
    print(f'Creating CSV at {pathToSave}')
    read_file.to_csv (pathToSave, index=None)
    removeFile(textPath)
    return True

def updateDict(dic:dict, args:dict)->dict:
    outDic = dic
    for k in args.keys():
        if k in dic.keys():
            outDic[k]= args[k]
    return outDic

def createDataframeFromArray(data, columns, csvPath:os.path= None)->pd.DataFrame:
    '''
    The function takes as input a numpy array and creates a pandas dataframe with the specified column names. 
    @data: numpy array
    @columns: list of column names
    @file_path: path to the CSV file. (Optional)
    @return: pd.DataFrame

    OPTIONAL: Save the DataFrame as csv file if csvPath is defined
    '''
    # print(f'Column names are : {len(columns)}')
    # print(f'Array shape : {data.shape}')
    df = pd.DataFrame(data, columns=columns)
    if csvPath:
        df.to_csv(csvPath, index=False)
    return df

def isCoordPairInArray(arr, pair) ->bool:
    '''
    Verify if a pair of coordinates values exist in the array. We asume that column[0] contain x_coordinates
    and column[1] contain y_coordinates
    The goal is to check if the coordinates of a map already exist in an array of map samples. 
    @pair: np.array like [x,y]
    @Return:Bool: True if pair is found, False otherwise.
    '''
    x, y = pair
    out = np.any(arr[np.where(arr[:,0]==x),1] == y)
    return out

###################            
### General GIS ###
###################

def plotImageAndMask(img, mask,imgName:str='Image', mskName: str= 'Mask'):
    # colList = ['Image','Mask']
    image = img.detach().numpy() if torch.is_tensor(img) else img.numpy().squeeze()
    mask_squeezed = mask.detach().numpy() if torch.is_tensor(mask) else mask.numpy().squeeze()
    fig, axs = plt.subplots(1,2, figsize=(10,5), sharey=True)
    axs[0].imshow(image, cmap='Greys_r')
    axs[0].set(xlabel= imgName)
    axs[1].imshow(mask_squeezed, cmap='Greys_r')
    axs[1].set(xlabel= mskName)
    plt.rcParams['font.size'] = '15'
    fig.tight_layout()
 
def imageToTensor(img,DTYPE:str = 'float32'):
    imagTensor = img.astype(DTYPE)
    # imagTensor = np.transpose(imagTensor, (2, 0, 1)).astype(DTYPE)
    imagTensor = torch.tensor(imagTensor)
    return imagTensor

def reshape_as_image(arr):
    '''
    From GDL
    Parameters
    ----------
    arr : arr as image in raster order (bands, rows, columns)
    return: array-like in the image form of (rows, columns, bands)
    '''       
    return np.ma.transpose(arr, [1, 2, 0]).astype('float32')

def reshape_as_raster(arr):
    '''  
    From GDL
        swap the axes order from (rows, columns, bands) to (bands, rows, columns)
    Parameters
    ----------
    arr : array-like in the image form of (rows, columns, bands)
    return: arr as image in raster order (bands, rows, columns)
    '''
    return np.transpose(arr, [2, 0, 1])

def plotHistComparison(DEM1,DEM2, bins:int = 50):
    # Reding raster 1:
    data_DEM1,_= readRasterWithRasterio(DEM1)  # Return an Array
    data_DEM1 = np.resize(data_DEM1,(1))
    # Reding raster 2:
    data_DEM2,_= readRasterWithRasterio(DEM2)  # Return an Array
    # data_DEM2 = np.resize(data_DEM2,(1))
    # Setting plot
    n_bins = bins
    fig, ax = plt.subplots(1,sharey=True, tight_layout=True)
    # x=np.array((data_DEM1[0],data_DEM2[0]))
    
    ax.hist(data_DEM1, n_bins, density=True, histtype='step', label=['cdem'],stacked=True, fill=False)
    # ax.hist(data_DEM2[0], n_bins, density=True, histtype='step', label=colors,stacked=True, fill=False)
    ax.legend(prop={'size': 10})
    ax.set_title('cdem_16m vs srdem_8m') 
    
    fig.tight_layout()
    plt.show()
    pass

def getNeighboursValues(raster)-> np.array:
    '''
    Inspect the 8 neighbours of each pixel to list their values. If the pixel being NoData, the neighbour list is empty. 
    @raster: os.path to the raster to inst=pect.
    @return: array of lists. 
    '''
    # Convert raster to NumPy array
    arr,profil = readRasterWithRasterio(raster)
    NOData = profil['nodata']
    # Get dimensions of array
    rows, cols = arr.shape

    # Create empty array to store neighbours
    neighbours = np.empty((rows, cols), dtype=object)

    # Iterate over each cell in array
    for i in range(rows):
        for j in range(cols):
            # Get value of current cell
            val = arr[i, j]

            # Check if value is NaN or NoData
            if np.isnan(val) or val == NOData:
                neighbours[i, j] = []
            else:
                # Get indices of neighbouring cells
                indices = [(i-1, j-1), (i-1, j), (i-1, j+1),
                           (i, j-1),             (i, j+1),
                           (i+1, j-1), (i+1, j), (i+1, j+1)]

                # Get values of neighbouring cells
                vals = [arr[x, y] for x, y in indices if 0 <= x < rows and 0 <= y < cols]
                # Add values to neighbours array
                neighbours[i, j] = vals

    return neighbours

def crop_TifList_WithMaskList(cfg: DictConfig, maskList:os.path):
    '''
    Given a list of polygons, the algorith find all tif files in the wdir and IF any names match ocurre, the tif is 
    cropped with the corresponding mask.
    '''
    wdir = cfg['output_dir']
    maskList = createListFromCSV(maskList)
    tifList = listFreeFilesInDirByExt_fullPath(wdir,'.tif')
    for i in tifList:
        _,tifName,_ = get_parenPath_name_ext(i)
        for j in maskList:
            _,maskName,_ = get_parenPath_name_ext(j)
            if maskName in tifName:
                outPath = os.path.join(wdir,maskName+'_clip.tif')
                print('-----------------------Cropping --------------------')
                crop_tif(i,j,outPath)
                print(f'{outPath}')
                print('-----------------------Cropped --------------------  \n')
    print("All done --->")        
    return True

def fromDEMtoDataFrame(DEM,labels,target:str='percentage',mask:os.path=None)->pd.DataFrame:
    '''
    Sampling automatically a DEM of multiples bands and a polygon, to produce a DataSet. 
    '''
    ## Create features for dataset
    bandsList = DEMFeaturingForMLP_WbT(DEM)
    ## Extract the band name from the list full path of features. Add column names for coordinates
    colList = extractNamesListFromFullPathList(bandsList,['x_coord','y_coord'])
    ## Build a multiband raster to ensure spatial correlation between features.
    rasterMultiband = addSubstringToName(DEM,'_features')
    stackBandsInMultibandRaster(bandsList,rasterMultiband)
    ## Crop the multiband raster if needed.
    if mask:
        cropped = addSubstringToName(rasterMultiband,'_AOI')
        raster = crop_tif(rasterMultiband,mask,cropped)
    else:
        raster = rasterMultiband
    ## Random sampling the raster with a density defined by the ratio. This is the more expensive opperation..by patient. 
    samplesArr = randomSamplingMultiBandRaster(raster,ratio=0.0001)
    ## Build a dataframe with the samples
    df = pd.DataFrame(samplesArr,columns=colList)
    ## Extract coordinates columns to sample from label. 
    xyList = samplesArr[:,0:2]
    content, nameList = sample_shapefile(labels,target,xyList)
    for name in nameList:
       df[name] = content[:,nameList.index(name)]
    ## Saving DataFrame as csv
    scv_output = replaceExtention(rasterMultiband,'_DataFrame.csv')
    df.to_csv(scv_output,index=None)
    return df

#######################
### Rasterio Tools  ###
#######################

def readRasterWithRasterio(rasterPath:os.path) -> tuple[np.array, dict]:
    '''
    Read a raster with Rasterio.
    return:
     Raster data as np.array
     Raster.profile: dictionary with all rater information
    '''
    inRaster = rio.open(rasterPath, mode="r")
    profile = inRaster.profile
    rasterData = inRaster.read()
    # print(f"raster data shape in ReadRaster : {rasterData.shape}")
    return rasterData, profile

def read_tiff_advanced(file_path: str) -> Tuple[np.ndarray, str, str]:
    try:
        with rio.open(file_path) as dataset:
            image_data = dataset.read()
            file_extension = dataset.profile['driver']
            crs = dataset.crs.to_string()
        return image_data, file_extension, crs
    except Exception as e:
        print(f"The TIFF in the path {file_path} is corrupted.")
        return None, None, None

def createRaster(savePath:os.path, data:np.array, profile, noData:int = None):
    '''
    parameter: 
    @savePath: Most contain the file name ex.: *name.tif.
    @data: np.array with shape (bands,H,W)
    '''
    B,H,W = data.shape[-3],data.shape[-2],data.shape[-1] 
    # print(f"C : {B}, H : {H} , W : {W} ")
    profile.update(dtype = rio.uint16, nodata = noData, blockysize = profile['blockysize'])
    with rio.open(
        savePath,
        mode="w",
        #out_shape=(B, H ,W),
        **profile
        ) as new_dataset:
            # print(f"New Dataset.Profile: ->> {new_dataset.profile}")
            new_dataset.write(data)
            print("Created new raster>>>")
    return savePath

def stackBandsInMultibandRaster(input_paths, output_path):
    '''
    Given a series of raster in the <input_path>, the algorithm create a multiband raster to the <output_path>.
    @input_path: List of path to a single band rasters.
    @output_path: Output path to save the multiband raster. 
    '''
    src_files_to_mosaic = []
    i = 0
    for path in input_paths:
        # print(f'band {i} : {path}')
        i+=1
        src = rio.open(path)
        src_files_to_mosaic.append(src)

    mosaic, out_trans = rio.merge.merge(src_files_to_mosaic)
    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                     "count": len(src_files_to_mosaic),
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans})

    with rio.open(output_path, "w", **out_meta) as dest:
        for i, file in enumerate(src_files_to_mosaic):
            dest.write(file.read(1), i+1)

def plotHistogram(raster, CustomTitle:str = None, bins: int=50, bandNumber: int = 1):
    if CustomTitle is not None:
        title = CustomTitle
    else:
        title = f"Histogram of band : {bandNumber}"    
    data,_ = readRasterWithRasterio(raster)
    
    show_hist(source=data, bins=bins, title= title, 
          histtype='stepfilled', alpha=0.5)
    return True

def replaceRastNoDataWithNan(rasterPath:os.path,extraNoDataVal: float = None)-> np.array:
    rasterData,profil = readRasterWithRasterio(rasterPath)
    NOData = profil['nodata']
    rasterDataNan = np.where(((rasterData == NOData)|(rasterData == extraNoDataVal)), np.nan, rasterData) 
    return rasterDataNan

def updateNoDataValue_Rio(input_path, output_path, nodata_value):
    with rio.open(input_path) as src:
        profile = src.profile
        profile.update(nodata=nodata_value)
        with rio.open(output_path, 'w', **profile) as dst:
            for i in range(1, src.count + 1):
                data = src.read(i)
                dst.write(data, i)

def computeRasterStats(rasterPath:os.path):
    '''
    Read a reaste and return: 
    @Return
    @rasMin: Raster min.
    @rasMax: Raster max.
    @rasMean: Rater mean.
    @rasMode: Raster mode.
    @rasSTD: Raster standard deviation.
    @rasNoNaNCont: Raster count of all NOT NoData pixels
    '''
    rasDataNan = replaceRastNoDataWithNan(rasterPath)
    rasMin = np.nanmin(rasDataNan)
    rasMax = np.nanmax(rasDataNan)
    rasMean = np.nanmean(rasDataNan)
    rasSTD = np.nanstd(rasDataNan)
    rasNoNaNCont = np.count_nonzero(rasDataNan != np.nan)
    # Compute mode
    vals,counts = np.unique(rasDataNan, return_counts=True)
    index = np.argmax(counts)
    rasMode = vals[index]
    return rasMin, rasMax, rasMean,rasMode, rasSTD, rasNoNaNCont

def computeRasterMinMax(rasterPath:os.path):
    '''
    Read a reaste and return: 
    @Return
    @rasMin: Raster min.
    @rasMax: Raster max.
    '''
    rasDataNan = replaceRastNoDataWithNan(rasterPath)
    rasMin = np.nanmin(rasDataNan)
    rasMax = np.nanmax(rasDataNan)
    return rasMin, rasMax

def computeRasterQuantiles(rasterPath, q:list=[0.25, 0.945]):
    rasDataNan = replaceRastNoDataWithNan(rasterPath)
    # rasDataNan,_ = readRasterWithRasterio(rasterPath)
    quantiles = np.nanquantile(rasDataNan, q)
    return quantiles

def computeRasterValuePercent(rasterPath, value:int=1)-> float:
    '''
    Compute the percent of pixels of value <value: default =1> in a raster. 
    @rasterPath: Path to the raster to be analyzed.
    @value: Value to verify percent in raster. Default = 1. 
    @return: The computed percent of <value> within the nonNoData values in the input raster.  
    '''
    rasDataNan = replaceRastNoDataWithNan(rasterPath)
    rasNoNaNCont = np.count_nonzero(rasDataNan != np.nan)
    valuCont = np.count_nonzero(rasDataNan == value)
    return (valuCont/rasNoNaNCont)*100

def normalize_raster(inputRaster):
    outputRaster = addSubstringToName(inputRaster, '_norm')
    with rio.open(inputRaster) as src:
        profile = src.profile
        with rio.open(outputRaster, 'w', **profile) as dst:
            for i in range(1, src.count + 1):
                data = src.read(i)
                normalized_data = (data - data.min()) / (data.max() - data.min())
                dst.write(normalized_data, i)
    return outputRaster

def randomSamplingMultiBandRaster(rasterIn,ratio:float=1)-> np.array:
    '''
    Given a multiband raster, the algorith, takes a random number of saples and retur in np.array format. 
    The samples are ONLY VALID points according the criteria of been not NODataValue. (bandsArray[0]!= NoData and bandsArray[0] != np.NAN)
    The samples are not repeated coordinates pairs.
    @rasterIn: the path to the input raster.
    @ratio: the proportion of existing pixels in the <rasterIn> to be sampled. 
    @return: np.array with a series of samplin points.
    '''
    sampleCont =0    
    arrayDataset = []
    with rio.open(rasterIn) as src:
        # Read data from bands into an array
        data = src.read()
        NoData = src.profile['nodata']
        W,H = src.width,src.height
        totalSamples = int((W*H)*ratio)
        print(f'Number of samples to take {totalSamples}')
        arrayDataset = np.zeros((totalSamples,(src.count+2)))
        while sampleCont<totalSamples:
            # Generate random index within the raster limits
            i = np.random.randint(0,H)
            j = np.random.randint(0,W)
            ## extract corrdinates at index (i,j)
            xy = np.array(src.xy(i,j))
            ## Extract banda values as vector
            bandsArray = data[:, i, j]
            # Check if neither value is NoData OR NaN in the first band (DEM)
            if (bandsArray[0]!= NoData and bandsArray[0] != np.NAN) and not isCoordPairInArray(arrayDataset,xy):
                # Add the sample to the dataset
                arrayDataset[sampleCont] = np.concatenate((xy, bandsArray))
                sampleCont+=1
                if sampleCont%1000 == 0:
                    print(f'{sampleCont-1} found') 
    return arrayDataset

def getRasterSampleFromPoint(raster,xy):
    '''
    Extract a sample from aa raster given a pari of coordinates xy.
      NOTE: This function do not make any veryfication.Important to ensure xy coordinates pair comes from the same crs of the raster.
    @xy: array of coordinates like [x,y].
    @raster: os.path to the raster to sample
    @return: a 1D array with the values of all the bands in the <raster> at the coordinates <xy>.
    '''
    x,y = xy
    with rio.open(raster) as src:
        # Read data from bands into an array
        data = src.read()
        bandsArray = data[:, x, y]
    return bandsArray

def transformShp_IDValue(shpFile, targetField, baseField):
# Open the shapefile
    driver = ogr.GetDriverByName('ESRI Shapefile')
    shapefile = driver.Open(shpFile, 1)  # 1 means open in update mode
    # Get the layer
    layer = shapefile.GetLayer()
    # Iterate over each feature in the layer
    for feature in layer:
        # Get the value of the field you want to base your changes on
        base_value = feature.GetField(baseField)
        # Determine the <new_value> based on the <base_value>
        # This is where you put your transformation logic
        new_value = str(base_value)  # replace this with your transformation function
        # Set and Update the value of the Layer's field.
        feature.SetField(targetField, new_value)
        layer.SetFeature(feature)

    # Close the shapefile
    shapefile = None

###########################
####   PCRaster Tools  ####
###########################

def computeHANDPCRaster(DEMPath,HANDPath,saveDDL:bool=True,saveStrahOrder:bool=True,saveSubCath:bool = False) -> os.path:
    '''
    NOTE: Important to ensure the input DEM has a well defined NoData Value ex. -9999. 

    1- *.tif in (DEMPath) is converted to PCRaster *.map format -> saveTiffAsPCRaster(DEM)
    2- pcr.setClone(DEMMap) : Ensure extention, CRS and other characteristics for creating new *.map files.
    3- Read DEM in PCRasterformat
    4- Compute flow direction with d8 algorithm -> lddcreate()
    5- Compute strahler Order-> streamorder(FlowDir)
    
    @DEMPath : Input path to the DEM in *.tif format.
    @HANDPath : Output path for the HAND.map result.
    
    '''
    ### Prepare output file path. 
    path,communName,_ = get_parenPath_name_ext(DEMPath)
    lddPath =os.path.join(path,str(communName+'_ldd.map'))
    strahleOrdPath =os.path.join(path,str(communName+'_StrOrder.map'))
    subCatch =os.path.join(path,str(communName+'_subCatch.map'))
    DEMMap = translateToPCRaster(DEMPath)
    pcr.setclone(DEMMap)
    DEM = pcr.readmap(DEMMap)
    aguila(DEM)
    ## Flow Direcction (Use to take long...)
    print("#####......Computing D8 flow dir.......######")
    threshold = 8
    FlowDir = lddcreate(DEM,1e31,1e31,1e31,1e31)
    if saveDDL: 
        pcr.report(FlowDir,lddPath)

    # Compute river network
    print('#####......Computing Strahler order.......######')
    strahlerOrder = streamorder(FlowDir)
    strahlerRiver = ifthen(strahlerOrder>=threshold,strahlerOrder)
    if saveStrahOrder:
        pcr.report(strahlerRiver, strahleOrdPath)
    
    print('#####......Finding outlets.......######')
    junctions = ifthen(downstream(FlowDir,strahlerOrder) != strahlerRiver, boolean(1))
    outlets = ordinal(cover(uniqueid(junctions),0))
    
    print('#####......Calculating subcatchment.......######')
    subCatchments = catchment(FlowDir,outlets)
    if saveSubCath:
        pcr.report(subCatchments,subCatch)
    
    # Compute HAND
    print('#####......Computing HAND.......######')
    areaMin = areaminimum(DEM,subCatchments)
    HAND = DEM - areaMin
    # Save HAND as *.map
    pcr.report(HAND,HANDPath)
    
    ##### Print maps
            ## Uncomment to show images of computed values. 
    # print('#####......Ready to print.......######')
    # aguila(HAND)
    # aguila(subCatchments)
    # aguila(areaMin)
    
    #Save HAND as *.tif
    handTifOut = replaceExtention(HANDPath,'.tif')
    translateToTiff(HANDPath,handTifOut)
    return handTifOut

def extractHydroFeatures(DEMPath) -> bool:
    '''
    NOTE: Important to ensure the input DEM has a well defined NoData Value ex. -9999. 
    1- *.tif in (DEMPath) is converted to PCRaster *.map format -> saveTiffAsPCRaster(DEM)
    2- pcr.setClone(DEMMap) : Ensure extention, CRS and other characteristics for creating new *.map files.
    3- Read DEM in PCRasterformat

    4- Compute strahler Order-> streamorder(FlowDir)
    5- Compute main river -> streamorder >= 10
    6- Extract outlets: Defines as outlet all the intersections in the river network.
    7- Compute subcatchment extention corresponding to each outlet.
    8- Compute flow accumulation (in cell numbers)

    Some other measurements are available as options. Uncomment the lines to compute and/or save. 
    
    @DEMPath : Input path to the DEM in *.tif format.
    @LDDPath : Input path to a precalculated LDD map through (pcr.lddcreation())
    @Return: <True> if the process is complete without error. Otherwhise, you'll receive an error from the PCRaster algorithm. 
    '''
    path,communName,_ = get_parenPath_name_ext(DEMPath)
    # Create output names
    slopePath = os.path.join(path,str(communName+'_slp.map'))
    lddOutPath = os.path.join(path,str(communName+'_ldd.map'))
    subCatchPath =os.path.join(path,str(communName+'_subCatch.map'))
    areaMinPath = os.path.join(path,str(communName+'_areaMin.map'))
    areaMaxPath = os.path.join(path,str(communName+'_areaMax.map'))
    outletsPath = os.path.join(path,str(communName+'_Outlets.map'))
    flowAccumulationPath = os.path.join(path,str(communName+'_FlowAcc.map'))
    maxFAccByCatchmentPath = os.path.join(path,str(communName+'_MaxFAccByCatch.map'))
    strahlerOrderPath = os.path.join(path,str(communName+'_StrahOrder.map'))
    mainRiverPath = os.path.join(path,str(communName+'_mainRiver_6Order.map'))
    HANDPath = os.path.join(path,str(communName+'_HANDMainRiver_SO6.map')) 
    
    pcr.setclone(DEMPath)
    DEM = pcr.readmap(DEMPath)
    print('#####......Computing Slope.......######')
    slp = slope(DEM)
    saveIt(slp,slopePath)
    
    print('#####......Computing LDD .......######')
    with timeit(): 
        FlowDir = lddcreate(DEM,1e31,1e31,1e31,1e31)
    saveIt(FlowDir,lddOutPath)
    print('#####......LDD Ready .......######')

    print('#####......Computing Strahler order and Main River.......######')
    threshold = 5
    strahlerOrder = streamorder(FlowDir)
    strahlerRiver = ifthen(strahlerOrder >=threshold,strahlerOrder)
    #####  Get Max strahler order
    array = pcraster.pcr2numpy(strahlerOrder, np.nan)
    # Get the maximum value
    max_value = np.nanmax(array)
    limit = int(max_value-(threshold - 1)) # MainRIver are the last <limit> numbers of Strahler Orders
    print(f'Max Satrahler order = {max_value}. For main river considered {limit} to {max_value}')
    
    ## Extract Main river with the 3 las strahler orders
    MainRiver = ifthen(strahlerOrder >= limit,strahlerOrder)
    saveIt(strahlerRiver,strahlerOrderPath)
    _,mainRiverTif = saveIt(MainRiver,mainRiverPath)
    print(f"Main_River.tif saved  --> {mainRiverTif} \n")
    
    print('#####......Finding outlets.......######')
    junctions = ifthen(downstream(FlowDir,strahlerOrder) != strahlerOrder, boolean(1))
    outlets = ordinal(cover(uniqueid(junctions),0))
    saveIt(outlets,outletsPath)

    print('#####......Calculating subcatchment.......######')
    subCatchments = catchment(FlowDir,outlets)
    # saveIt(subCatchments,subCatchPath)
    
    print('#####......Computing subcatchment measures.......######')
    massMap = pcr.spatial(pcr.scalar(1.0))
    flowAccumulation = accuflux(FlowDir, massMap)
    MaxFAccByCatchment = areamaximum(flowAccumulation,subCatchments)
    areaMin = areaminimum(DEM,subCatchments)    # Optional
    areaMax = areamaximum(DEM,subCatchments)    # Optional
    
    ## Compute HAND
    print('#####......Computing HAND.......######')
    HAND = DEM - areaMin
    # Save HAND as *.map
    saveIt(HAND,HANDPath)
    
    print('#####......Saving subcatchment measures.......######')
    ## Saving subcatchment measures
    saveIt(flowAccumulation,flowAccumulationPath)
    # saveIt(areaMin,areaMinPath)    # Optional
    saveIt(areaMax,areaMaxPath)    # Optional
    saveIt(MaxFAccByCatchment,maxFAccByCatchmentPath)
    del DEM,areaMax,massMap,flowAccumulation,MaxFAccByCatchment,subCatchments,outlets,junctions,MainRiver,strahlerRiver,strahlerOrder,FlowDir
    return mainRiverTif

def saveIt(dataset, path):
        pcr.report(dataset,path)
        path_Reproj = assigneProjection(path)
        translatedTIff = translateToTiff(path_Reproj)
        if path_Reproj and (path != path_Reproj):
            removeFile(path)
            return path_Reproj,translatedTIff
        else:
            return path,translatedTIff

######################
####   GDAL Tools  ###
######################

class RasterGDAL():
    '''
    Some info about GDAL deo Transform
    adfGeoTransform[0] /* top left x */
    adfGeoTransform[1] /* w-e pixel resolution */
    adfGeoTransform[2] /* rotation, 0 if image is "north up" */
    adfGeoTransform[3] /* top left y */
    adfGeoTransform[4] /* rotation, 0 if image is "north up" */
    adfGeoTransform[5] /* n-s pixel resolution */
    
    '''
    def __init__(self, rasterPath) -> None:
        gdal.AllRegister() # register all of the drivers
        gdal.DontUseExceptions()
        self.inputPath = rasterPath
        self.ds = gdal.Open(rasterPath)
        if self.ds is None:
            print('Could not open image')
            sys.exit(1)   
        # get image size
        self.rows = self.ds.RasterYSize
        self.cols = self.ds.RasterXSize
        self.NumOfBands = self.ds.RasterCount
        # get georeference info
        transform = self.ds.GetGeoTransform()
        self.xOrigin = transform[0]
        self.yOrigin = transform[3]
        self.pixelWidth = transform[1]
        self.pixelHeight = transform[5]
        self.projection = self.ds.GetProjection()
        self.MetaData = self.ds.GetMetadata()
        self.band1 = self.ds.GetRasterBand(1)
        self.NoData = self.band1.GetNoDataValue()

    def setDirGDAL(self, path ):
        os.chdir()
    
    def getRasterDataset(self):
        return self.ds 
   
    def getRasterNpArray(self, maskNoData:bool = True)-> np.array:
        arr = self.ds.ReadAsArray()
        if maskNoData:
            arr = np.ma.masked_equal(arr, self.NoData)
        return arr
    
    def computePixelOffset(self,x,y):
        # compute pixel offset
        xOffset = int((x - self.xOrigin) / self.pixelWidth)
        yOffset = int((y - self.yOrigin) / self.pixelHeight)
        return xOffset, yOffset

    def closeRaster(self):
        self.ds = None

    def translateRaster(self, outpPath, format:str = "GeoTiff"):
        """
        Ref: https://gdal.org/api/python/osgeo.gdal.html#osgeo.gdal.Translate
        """
        gdal.Translate(outpPath,self.ds,format=format)
        return True

    def saveTiffAsPCRaster(self):
        outpPath = ntpath.basename(self.inputPath).replace('.tif','.map') 
        gdal.Translate(outpPath,self.ds,format='PCRaster')
        return outpPath

    def printRaster(self):
        print("---- Image size ----")
        print(f"Row : {self.rows}")
        print(f"Cols : {self.cols}")
        print(f"xOrigin : {self.xOrigin}")
        print(f"yOrigin : {self.yOrigin}") 
        print(f"NumOfBands : {self.NumOfBands}")
        print(f"pixelWidth : {self.pixelWidth}")
        print(f"pixelHeight : {self.pixelHeight}")
        print(f"projection : {self.projection}")
        print(f"MetaData : {self.MetaData}")

def replace_no_data_value(dataset_path, new_value:float = -9999):
    dataset = gdal.Open(dataset_path, gdal.GA_Update)
    for i in range(1, dataset.RasterCount + 1):
        band = dataset.GetRasterBand(i)
        old_value = band.GetNoDataValue()
        band = dataset.GetRasterBand(i)
        band_array = band.ReadAsArray()
        band_array[band_array == old_value] = new_value
        band.WriteArray(band_array)
        band.SetNoDataValue(new_value)
    dataset.FlushCache()

def translateToTiff(inPath) -> bool:
    """
    Write a *tif raster from an appropriate(GDAL accepted formats) raster input. The function return a raster with the same characteristic,
      with NoDataValue seted to -9999.
    @inPath: os.path: Path to the input raster
    @Return: os.path: Path to the *.tif raster. 
    
    """
     # Open the input raster
    input_raster = gdal.Open(inPath)
   
    # Transform the dataset NoData value into -9999
    input_band = input_raster.GetRasterBand(1)
    input_band.SetNoDataValue(-9999)

    # Create an empty raster file with the same CRS as the input raster
    output_path = os.path.splitext(inPath)[0] + '.tif'
    driver = gdal.GetDriverByName('GTiff')
    output_raster = driver.CreateCopy(output_path, input_raster, 0)

    # Write the dataset with the transformed NoData into the empty raster
    output_band = output_raster.GetRasterBand(1)
    output_band.WriteArray(input_band.ReadAsArray())

    # Close the rasters
    input_raster = None
    output_raster = None

    return output_path

def translateToPCRaster(inputPath) -> str:
    outpPath = replaceExtention(inputPath,'.map')
    options = gdal.TranslateOptions(format='PCRaster',noData=-9999) # creationOptions=["COMPRESS=LZW"]
    gdal.Translate(outpPath,inputPath,options=options) #outputType=gdal.GDT_Float32
    return outpPath

def readRasterAsArry(rasterPath):
   return gdal_array.LoadFile(rasterPath)

def extractProjection(inPath):
    '''
    Extract the projection of the dataset with GDAL.GetProjection()
    @inPath: path to the input file. Must be in one of the GDAL format. ex. 'GTiff'
    @Return: projection file
    '''
    # Open the input TIFF file
    dataset = gdal.Open(inPath)
    # Get the input CRS
    crs = dataset.GetProjection()
    print(crs)
    return crs

def reproject_PCRaster(tif_file,output_crs:str='EPSG:3979') -> str:
    """
    Reprojects a PCraster file to the specified coordinate reference system (CRS).
    Args:
        map_file(str): Path to the input *.map file.
        output_crs (str): Output coordinate reference system (CRS) in the format 'EPSG:<code>'.

    Returns:
        str: Path to the reprojected *.map file.
    NOTE: NOData value do not works. 
    """
    # get input name and extention
    parent,inputNeme,ext = get_parenPath_name_ext(tif_file)
    # Open the input TIFF file
    dataset = gdal.Open(tif_file)
    
    # Create a spatial reference object for the output CRS
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(int(output_crs.split(':')[1]))
    output_file_path = os.path.join(parent,inputNeme + '_' + ext)
    
    # Create the output dataset
    '''
    NO definas input dataset crs. 
       srcSRS=input_srs, 
    '''
    gdal.Warp(output_file_path, dataset, dstSRS=output_srs, outputType=gdal.GDT_Float32, dstNodata=-9999, creationOptions=['PCRASTER_VALUESCALE=VS_SCALAR'])
    # gdal.Warp(output_file_path, dataset, dstSRS=output_srs, resampleAlg=gdal.GRA_Bilinear, dstNodata=-9999,outputType=gdal.GDT_Float32)
    # Close the datasets
    del dataset
    return output_file_path

def reproject_tif(tif_file, output_crs:str='EPSG:3979') -> str:
    """
    Reprojects a TIFF file to the specified coordinate reference system (CRS).
    Args:
        tif_file (str): Path to the input TIFF file.
        output_crs (str): Output coordinate reference system (CRS) in the format 'EPSG:<code>'. Default <'EPSG:3979'>

    Returns:
        str: Path to the reprojected TIFF file.
    """
    # get input name and extention
    parent,inputNeme,ext = get_parenPath_name_ext(tif_file)
    # Open the input TIFF file
    replace_no_data_value(tif_file)
    dataset = gdal.Open(tif_file,gdal.GA_Update)
    # Create a spatial reference object for the output CRS
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(int(output_crs.split(':')[1]))
    output_file_path = os.path.join(parent,inputNeme + '_' + ext)
    
    # Create the output dataset
    '''
    Do not define input dataset crs. 
       srcSRS=input_srs, 
    It works better. Do not know way..!!
    '''
    gdal.Warp(output_file_path, dataset, dstSRS=output_srs, resampleAlg=gdal.GRA_Bilinear, dstNodata=-9999)#outputType=gdal.GDT_Float32
    # Close the datasets
    del dataset
    return output_file_path

def assigneProjection(raster_file, output_crs:str='EPSG:3979') -> str:
    '''
    Assigne prejection <outpt_crs> to files in *.tif and *.map format IF they have no projection defined.
    parameters:
     @raster_file: os.path: Path to the raster to be reprojected.
     @output_crs: <EPSG:####> projection.
     @return: The path to the reprojected file.
    '''
    _,communName,ext = get_parenPath_name_ext(raster_file)
    input_crs = extractProjection(raster_file)
    if not input_crs:
        print(f'Reprojecting..... {communName}{ext}')
        if "map" in ext:
            return reproject_PCRaster(raster_file,output_crs)
        if 'tif' in ext:
            return reproject_tif(raster_file,output_crs) 

def crop_tif(inputRaster:os.path, maskVector:os.path, outPath:os.path)->os.path:
    """
    Crops a TIFF file using a shapefile as a mask.
    NOTE: It is important to FILL THE NEW DATASET WITH np.nan to avoid ending with big extentions of valid values, instead of NoData. 

    Args:
        inputRaster (str): Path to the input TIFF file.
        maskVector (str): Path to the input shapefile.
        outPath (str): Path to the output TIFF file.
    Returns:
        str: Path to the output TIFF file.
    """
    # Open the input TIFF file
    dataset = gdal.Open(inputRaster)
    cols = dataset.RasterXSize
    rows = dataset.RasterYSize
    count = dataset.RasterCount
    datatype = gdal.GetDataTypeName(dataset.GetRasterBand(1).DataType)
    print(f'cols,rows: {cols}:--{rows}')
    print(f'datatype: {datatype}')
    # Open the shapefile
    shapefile_ds = ogr.Open(maskVector)
    layer = shapefile_ds.GetLayer()
    # Get the extent of the shapefile
    extent = layer.GetExtent()
    print(f'extent: {extent}')
    # Set the output file format
    driver = gdal.GetDriverByName('GTiff')
    # Create the output dataset
    output_dataset = driver.Create(outPath, cols,rows,count, gdal.GDT_Float32)
    output_dataset.GetRasterBand(1).SetNoDataValue(-9999)  # Important step to ensure DO NOT FILL the whole extention with valid values. 
    # Set the geotransform and projection
    output_dataset.SetGeoTransform(dataset.GetGeoTransform())
    output_dataset.SetProjection(dataset.GetProjection())
    # Perform the cropping
    print(f'output_dataset: {output_dataset}')
    gdal.Warp(output_dataset, dataset, outputBounds=extent, cutlineDSName=maskVector, cropToCutline=True)
    # ,cutlineLayer = 'bc_quesnel'
    # Close the datasets
    dataset = output_dataset= shapefile_ds = None
    return outPath

def clipRasterByMask(DEMPath:os.path, vectorMask, outPath)-> gdal.Dataset:
    '''
    Simplified version of crop_tif() WORKS well! However, do not perform extra operations like correct NoData or verify crs.
    If you are sure of your inputs and outputs, use it.
    '''
    mask_bbox = get_Shpfile_bbox(vectorMask)
    gdal.Warp(outPath, DEMPath,outputBounds=mask_bbox,cutlineDSName=vectorMask, cropToCutline=True)
    print(f"Successfully clipped at : {outPath}")
    return outPath

def get_Shpfile_bbox(file_path) -> Tuple[float, float, float, float]:
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(file_path, 0)
    layer = data_source.GetLayer()
    extent = layer.GetExtent()
    min_x, max_x, min_y, max_y = extent
    return min_x, min_y, max_x, max_y

def get_Shpfile_bbox_str(file_path) -> str:
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(file_path, 0)
    layer = data_source.GetLayer()
    extent = layer.GetExtent()
    min_x, max_x, min_y, max_y = extent
    bboxStr = str(round(min_x, 2))+','+str(round(min_y,2))+','+str(round(max_x,2))+','+str(round(max_y,2))
    return bboxStr

def computeProximity(inRaster, value:int= 1, outPath:os.path = None) -> os.path:
    '''
    Compute the horizontal distance to features in the input raster.
    @inRaster: A raster with features to mesure proximity from. A 0-1 valued raster,where the 1s are cells of the river network. 
    @outPath: Path to save the output raster. If None,the output is create in the same folder as the input with prefix: <_proximity.tif>.
    @values: list of values to be considered as terget in the inRaster. Default [1].  
    '''
    if outPath is None:  
        path,communName,_ = get_parenPath_name_ext(inRaster)
        # Create output name
        outPath =os.path.join(path,str(communName+'_proximity.tif'))
    ds = gdal.Open(inRaster,GA_ReadOnly)
    band = ds.GetRasterBand(1)
    gt = ds.GetGeoTransform()
    sr = ds.GetProjection()
    cols = ds.RasterXSize
    rows = ds.RasterYSize

    # create empty proximity raster
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(outPath, cols, rows, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(sr)
    out_band = out_ds.GetRasterBand(1)

    # compute proximity
    gdal.ComputeProximity(band, out_band, [f'VALUES= {value}', 'DISTUNITS=GEO'])
    # delete input and output rasters
    del ds, out_ds
    return outPath

def getNeighborsGDAL(raster_file, shape_file):
    """
    This function takes a raster and a shapefile as input and returns an array containing
    the values of the 8 neighbors of each pixel in the raster. The inputs must be in the
    same reference system. The output array will have the same size of the input raster
    and will contain at each cell a list of shape [1:8], with the values of the 8 neighbors
    of the questioned pixel, starting from the left up corner. The function considers only
    the pixels that are not np.nan or noData value in any of the two input layers. If the
    questioned pixel is noData in any of the inputs or np.nan, the list of neighbors values
    will be empty.
                               Neighbourhood order
                                #############
                                ## 1  2  3 ##
                                ## 4  X  5 ##
                                ## 6  7  8 ##
                                #############

    @raster_file: path to raster file.
    @shape_file: path to shapefile.
    @return: array containing values of 8 neighbors for each pixel in raster
    """
    # Open raster file and get band, width, height, and transform information
    dataset = gdal.Open(raster_file)
    band = dataset.GetRasterBand(1)
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    transform = dataset.GetGeoTransform()

    # Open shapefile and get layer information
    shape = gdal.OpenEx(shape_file)
    layer = shape.GetLayer()

    # Create output array with same size as input raster
    output_array = np.empty((height, width), dtype=object)

    # Loop through each pixel in raster and get its neighbors' values
    for y in range(height):
        for x in range(width):
            # Get value at current pixel location
            value = band.ReadAsArray(x, y, 1, 1)[0][0]

            # Check if current pixel is not np.nan or noData value in either input layer
            if not np.isnan(value) and value != band.GetNoDataValue():
                # Get coordinates for current pixel location
                x_coord = transform[0] + (x * transform[1]) + (y * transform[2])
                y_coord = transform[3] + (x * transform[4]) + (y * transform[5])

                ## Create polygon for current pixel location
                # This could be slow, but is less error-prone than rasterize polygons. 
                ring = ogr.Geometry(ogr.wkbPolygon)
                ring.AddPoint(x_coord, y_coord)
                ring.AddPoint(x_coord + transform[1], y_coord)
                ring.AddPoint(x_coord + transform[1], y_coord + transform[5])
                ring.AddPoint(x_coord, y_coord + transform[5])
                ring.AddPoint(x_coord, y_coord)
                poly = ogr.Geometry(ogr.wkbPolygon)
                poly.AddGeometry(ring)

                # Loop through each feature in shapefile and check if it intersects with current pixel location polygon
                neighbors = []
                for feature in layer:
                    if feature.GetGeometryRef().Intersects(poly):
                        neighbor_value = feature.GetField("value")
                        if not np.isnan(neighbor_value) and neighbor_value != band.GetNoDataValue():
                             # Get indices of neighbouring cells
                            indices = [(x_coord-transform[0], y_coord-transform[3]),        #1
                                    (x_coord-transform[0], y_coord),                        #2
                                    (x_coord-transform[0], y_coord+transform[3]),           #3
                                    (x_coord, y_coord-transform[3]),                        #4
                                    (x_coord, y_coord+transform[3]),                        #5
                                    (x_coord+transform[0], y_coord-transform[3]),           #6
                                    (x_coord+transform[0], y_coord),                        #7
                                    (x_coord+transform[0], y_coord+transform[3])]           #8

                            # Get values of neighbouring cells that are not NaN or NoData in either input layer
                            vals = [band[x, y] for x, y in indices]
                            # Add values to neighbours array
                            neighbors[x_coord, y_coord] = vals
                # Add list of neighbor values to output array at current pixel location
                output_array[y,x] = neighbors

            else:
                # Add empty list to output array at current pixel location since current pixel is noData or np.nan
                output_array[y,x] = []

    return output_array

def fullSamplingTwoFasterForComparison(raster1_path, raster2_path) -> np.array:
    '''
    This code takes two input rasters and returns an array with four columns: [x_coordinate, y_coordinate, Z_value  raster one, Z_value raster two]. 
    The first input raster is used as a reference. 
    The two rasters are assumed to be in the same CRS but not necessarily with the same resolution. 
    The algorithm samples the centre of all pixels using the upper-left corner of the first raster as a reference.
    When you read a raster with GDAL, the raster transformation is represented by a <geotransform>. The geotransform is a six-element tuple that describes the relationship between pixel coordinates and georeferenced coordinates ⁴. The elements of the geotransform are as follows:
    
    RASTER Transformation content 
    ex. raster_transformation : (1242784.0, 8.0, 0.0, -497480.0, 0.0, -8.0)
    0. x-coordinate of the upper-left corner of the raster
    1. width of a pixel in the x-direction
    2. rotation, which is zero for north-up images
    3. y-coordinate of the upper-left corner of the raster
    4. rotation, which is zero for north-up images
    5. height of a pixel in the y-direction (usually negative)

    The geotransform to convert between pixel coordinates and georeferenced coordinates using the following equations:

    x_geo = geotransform[0] + x_pixel * geotransform[1] + y_line * geotransform[2]
    y_geo = geotransform[3] + x_pixel * geotransform[4] + y_line * geotransform[5]

    `x_pixel` and `y_line` : pixel coordinates of a point in the raster, 
    `x_geo` and `y_geo` : corresponding georeferenced coordinates.

    In addition, to extract the value in the centre of the pixels, we add 1/2 of width and height respectively.
    x_coord = i * raster1_transform[1] + raster1_transform[0] + raster1_transform[1]/2 
    y_coord = j * raster1_transform[5] + raster1_transform[3] + raster1_transform[5]/2

    '''
    # Open the first raster and get its metadata
    raster1 = gdal.Open(raster1_path)
    raster1_transform = raster1.GetGeoTransform()
    print(f"raster1_transform : {raster1_transform}")
    raster1_band = raster1.GetRasterBand(1)
    raster1_noDataValue = raster1_band.GetNoDataValue()

    # Open the second raster and get its metadata
    raster2 = gdal.Open(raster2_path)
    raster2_transform = raster2.GetGeoTransform()
    raster2_band = raster2.GetRasterBand(1)
    raster2_noDataValue = raster2_band.GetNoDataValue()

    # Get the size of the rasters
    x_size = raster1.RasterXSize
    y_size = raster1.RasterYSize

    # Create an array to store the sampled points
    sampled_points = np.zeros((x_size * y_size, 4))

    # Loop through each pixel in the first raster
    
    for i in range(x_size):
        for j in range(y_size):
            # Get the coordinates of the pixel in the first raster
            x_coord = i * raster1_transform[1] + raster1_transform[0] + raster1_transform[1]/2 
            y_coord = j * raster1_transform[5] + raster1_transform[3] + raster1_transform[5]/2 

            # Get the value of the pixel in the first and second rasters
            value_raster1 = raster1_band.ReadAsArray(i, j, 1, 1)[0][0]
            value_raster2 = raster2_band.ReadAsArray(i, j, 1, 1)[0][0]

            # Add the sampled point to the array
            if (value_raster1!= raster1_noDataValue and value_raster1 != np.NaN 
                and value_raster2 != raster2_noDataValue and value_raster2 != np.NaN):
                sampled_points[i * y_size + j] = [x_coord, y_coord, value_raster1, value_raster2]

    print(f'One sample: {sampled_points[2:]}')
    return sampled_points
    
def randomSamplingTwoRaster(raster1_path, raster2_path, num_samples) -> np.array:
    '''
    This code takes two input rasters and returns an array with four columns: [x_coordinate, y_coordinate, Z_value rather one, Z_value rather two]. 
    The first input raster is used as a reference. 
    The two rasters are assumed to be in the same CRS but not necessarily with the same resolution. 
    The algorithm samples the centre of all pixels using the upper-left corner of the first raster as a reference.
    When you read a raster with GDAL, the raster transformation is represented by a <geotransform>. The geotransform is a six-element tuple that describes the relationship between pixel coordinates and georeferenced coordinates ⁴. The elements of the geotransform are as follows:
    
    RASTER Transformation content 
    ex. raster_transformation : (1242784.0, 8.0, 0.0, -497480.0, 0.0, -8.0)
    0. x-coordinate of the upper-left corner of the raster
    1. width of a pixel in the x-direction
    2. rotation, which is zero for north-up images
    3. y-coordinate of the upper-left corner of the raster
    4. rotation, which is zero for north-up images
    5. height of a pixel in the y-direction (usually negative)

    The geotransform to convert between pixel coordinates and georeferenced coordinates using the following equations:

    x_geo = geotransform[0] + x_pixel * geotransform[1] + y_line * geotransform[2]
    y_geo = geotransform[3] + x_pixel * geotransform[4] + y_line * geotransform[5]

    `x_pixel` and `y_line` : pixel coordinates of a point in the raster, 
    `x_geo` and `y_geo` : corresponding georeferenced coordinates.

    In addition, to extract the value in the centre of the pixels, we add 1/2 of width and height respectively.
    x_coord = i * raster1_transform[1] + raster1_transform[0] + raster1_transform[1]/2 
    y_coord = j * raster1_transform[5] + raster1_transform[3] + raster1_transform[5]/2

    '''    
    
    # Get the shape of the rasters
    # Open the first raster and get its metadata
    raster1 = gdal.Open(raster1_path)
    raster1_transform = raster1.GetGeoTransform()
    # print(f"raster1_transform : {raster1_transform}")
    raster1_band = raster1.GetRasterBand(1)
    raster1_noDataValue = raster1_band.GetNoDataValue()

    # Open the second raster and get its metadata
    raster2 = gdal.Open(raster2_path)
    raster2_transform = raster2.GetGeoTransform()
    raster2_band = raster2.GetRasterBand(1)
    raster2_noDataValue = raster2_band.GetNoDataValue()

    # Get the size of the rasters
    x_size = raster1.RasterXSize
    y_size = raster1.RasterYSize
    # print(f"size x, y : {x_size} , {y_size}")

    # Create an empty array to store the samples
    samples = np.zeros((num_samples, 4))
    # Loop through the number of samples
    sampleCont = 0
    while sampleCont<num_samples:
        i = np.random.randint(0, x_size)
        j = np.random.randint(0, y_size)
        # Generate random coordinates within the raster limits
        x = i * raster1_transform[1] + raster1_transform[0]+ raster1_transform[1]/2 
        y = j * raster1_transform[5] + raster1_transform[3]+ raster1_transform[5]/2 
        
        # Extract the values from the two rasters at the selected coordinates
        value1 = raster1_band.ReadAsArray(i, j, 1, 1)[0][0]
        value2 = raster2_band.ReadAsArray(i, j, 1, 1)[0][0]

        # Check if neither value is : NoData OR NaN
        if (value1!= raster1_noDataValue and value1 != np.NaN and value2 != raster2_noDataValue and value2 != np.NaN):
            # Add the values to the samples array
            samples[sampleCont] = [x, y, value1, value2]
            sampleCont+=1    

    return samples

def getFieldValueFromPolygon(vector_path, field_name, x, y)->list:
    # Open the vector file
    vector = ogr.Open(vector_path)
    layer = vector.GetLayer()
    # Create a point geometry for the given coordinate pair
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(x,y)
    # Set up a spatial filter to select features that intersect with the point
    layer.SetSpatialFilter(point)
    # Get the value of the specified field for each intersecting feature
    values = []
    for feature in layer:
        values.append(feature.GetField(field_name))
    # Return the first value if there is at least one intersecting feature
    if values:
        return values
    else:
        return []

def getFieldValueFromPolygonLayer(layer:ogr.Layer, field_name, x,y)->list:
    # Create a point geometry for the given coordinate pair
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(x,y)
    # Set up a spatial filter to select features that intersect with the point
    layer.SetSpatialFilter(point)
    # Get the value of the specified field for each intersecting feature
    values = []
    for feature in layer:
        values.append(feature.GetField(field_name))
    # Return the first value if there is at least one intersecting feature
    if values:
        return values
    else:
        return []

def getRasterValueByCoord(raster1_path, xy) -> np.array:
    '''
    This code takes two input rasters and returns an array with four columns: [x_coordinate, y_coordinate, Z_value rather one, Z_value rather two]. 
    The first input raster is used as a reference. 
    The two rasters are assumed to be in the same CRS but not necessarily with the same resolution. 
    The algorithm samples the centre of all pixels using the upper-left corner of the first raster as a reference.
    When you read a raster with GDAL, the raster transformation is represented by a <geotransform>. The geotransform is a six-element tuple that describes the relationship between pixel coordinates and georeferenced coordinates ⁴. The elements of the geotransform are as follows:
    
    RASTER Transformation content 
    ex. raster_transformation : (1242784.0, 8.0, 0.0, -497480.0, 0.0, -8.0)
    0. x-coordinate of the upper-left corner of the raster
    1. width of a pixel in the x-direction
    2. rotation, which is zero for north-up images
    3. y-coordinate of the upper-left corner of the raster
    4. rotation, which is zero for north-up images
    5. height of a pixel in the y-direction (usually negative)

    The geotransform to convert between pixel coordinates and georeferenced coordinates using the following equations:

    x_geo = geotransform[0] + x_pixel * geotransform[1] + y_line * geotransform[2]
    y_geo = geotransform[3] + x_pixel * geotransform[4] + y_line * geotransform[5]

    `x_pixel` and `y_line` : pixel coordinates of a point in the raster, 
    `x_geo` and `y_geo` : corresponding georeferenced coordinates.

    In addition, to extract the value in the centre of the pixels, we add 1/2 of width and height respectively.
    x_coord = i * raster1_transform[1] + raster1_transform[0] + raster1_transform[1]/2 
    y_coord = j * raster1_transform[5] + raster1_transform[3] + raster1_transform[5]/2

    '''    
    
    # Get the shape of the rasters
    # Open raster and get its metadata
    raster1 = gdal.Open(raster1_path)
    raster1_band = raster1.GetRasterBand(1)
    # Create an empty array to store the samples
    rows = xy.shape[0]
    samples = np.zeros([rows,1])
    # Loop through the number of samples
    idx = 0
    for x,y in xy:
        # Extract the values from the two rasters at the selected coordinates
        value1 = raster1_band.ReadAsArray(x, y, 1, 1)[0][0]
        # Check if neither value is : NoData OR NaN):
            # Add the values to the samples array
        samples[idx] = [value1]
        idx+=1    
    return samples


############################
#### Datacube_ Extract  ####
############################

def dc_describe(cfg: DictConfig)-> bool:
    '''
    Configurate the call of d.describe() with hydra parameters.
    '''
    instantiate(OmegaConf.create(cfg.dc_Extract_params['dc_describeCollections']))
    return True

def dc_search(cfg: DictConfig)-> str :
    '''
    Configurate the call of d.search()  with hydra parameters.
    return the output path of the search result.
    '''
    out = instantiate(OmegaConf.create(cfg.dc_Extract_params['dc_search']))
    return out

def dc_extraction(cfg: DictConfig, args:dict=None)-> str:
    '''
    Configurate the call of extract_cog() with hydra parameters.
    return the output path of the extracted file.
    '''
    dict_DcExtract = OmegaConf.create(cfg.dc_Extract_params['dc_extrac_cog'])
    if args is not None:
        dict_DcExtract = updateDict(dict_DcExtract,args)
    print(f"New dcExtract Dict:  {dict_DcExtract}")
    ##  procede to extraction
    out = instantiate(dict_DcExtract)
    return out

def multiple_dc_extract_ByPolygonList(cfg: DictConfig):
    '''
    @cfg: DictConfig
    @csvPolygonList
    @Return: True if no error, otherwise dc_extraction tool errors report.
    '''
    polygList = createListFromCSV(cfg.dc_Extract_params['polygonListCSV'])
    for polyg in polygList:
        if os.path.exists(polyg):
            print(f"Currently working on -> {polyg}")
            _,name,_ = get_parenPath_name_ext(polyg)
            bbox = get_Shpfile_bbox_str(polyg)
            args = {"bbox":bbox,"suffix":name}
            dc_extraction(cfg,args=args)
        else:
            print(f"Path not found in the ssytem -> {polyg}")
    return True

######################################
####   WhiteBoxTools and  Rasterio ###
######################################

## LocalPaths and global variables: to be adapted to your needs ##

wbt = WhiteboxTools()
# currentDirectory = os.getcwd()
# wbt.set_working_dir(currentDirectory)
wbt.set_verbose_mode(False)
wbt.set_compress_rasters(True) # compress the rasters map. Just ones in the code is needed

    ## Pretraitment #
class WbT_DEM_FeatureExtraction():
    '''
     This class contain some functions to generate geomorphological and hydrological features from DEM.
    Functions are based on WhiteBoxTools and Rasterio libraries. For optimal functionality DTM’s most be high resolution, ideally Lidar derived  1m or < 2m. 
    '''
    def __init__(self,DEM) -> None:
        self.parentDir,_,_ = get_parenPath_name_ext(DEM)
        self.DEMName = DEM
        self.FilledDEM = addSubstringToName(DEM,'_fill')
        wbt.set_working_dir(self.parentDir)
        print(f"Working dir at: {self.parentDir}")    

    def computeSlope(self):
        outSlope = addSubstringToName(self.FilledDEM,'_Slope')
        wbt.slope(self.DEMName,
                outSlope, 
                zfactor=None, 
                units="degrees", 
                callback=default_callback
                )
        return outSlope
    
    def computeAspect(self):   
        outAspect = addSubstringToName(self.FilledDEM,'_aspect')
        wbt.aspect(self.DEMName, 
                outAspect, 
                zfactor=None, 
                callback=default_callback
                )
        return outAspect
    
    def fixNoDataAndfillDTM(self,eraseIntermediateRasters = True)-> os.path:
        '''
        Ref:   https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#filldepressions
        To ensure the quality of this process, this method execute several steep in sequence, following the Whitebox’s authors recommendation (For mor info see the above reference).
        Steps:
        1-	Correct no data values to be accepted for all operation. 
        2-	Fill gaps of no data.
        3-	Fill depressions.
        4-	Remove intermediary results to save storage space (Optionally you can keep it. See @Arguments).  
        @Argument: 
        -self.DEMName: Input DEM name
        -eraseIntermediateRasters(default = True): Erase intermediate results to save storage space. 
        @Return: True if all process happened successfully, ERROR messages otherwise. 
        @OUTPUT: DEM <_fillWL> Corrected DEM with wang_and_liu method. 
        '''
        dtmNoDataValueSetted = addSubstringToName(self.DEMName,'_NoDataOK')
        wbt.set_nodata_value(
            self.DEMName, 
            dtmNoDataValueSetted, 
            back_value=0.0, 
            callback=default_callback
            )
        dtmMissingDataFilled = addSubstringToName(self.DEMName,'_MissingDataFilled')
        wbt.fill_missing_data(
            dtmNoDataValueSetted, 
            dtmMissingDataFilled, 
            filter=11, 
            weight=2.0, 
            no_edges=True, 
            callback=default_callback
            )
        wbt.fill_depressions_wang_and_liu(
            dtmMissingDataFilled, 
            self.FilledDEM, 
            fix_flats=True, 
            flat_increment=None, 
            callback=default_callback
            )
        if eraseIntermediateRasters:
            try:
                os.remove(os.path.join(wbt.work_dir,dtmNoDataValueSetted))
                os.remove(os.path.join(wbt.work_dir,dtmMissingDataFilled))
            except OSError as error:
                print("There was an error removing intermediate results : \n {error}")
        return self.FilledDEM

    def d8_Pointer(self)-> os.path:
        '''
        Compute single flow direction based on the D* algorithm. Each cell is assigned with the direction pointing to the lowest neighbour.  
        @argument:
         @inFilledDTMName: DEM without spurious points are depression.  
        @UOTPUT: D8_pioter: Raster to use as input for flow direction and flow accumulation calculations. 
        '''
        output = addSubstringToName(self.FilledDEM,"_d8Pointer")
        wbt.d8_pointer(
            self.FilledDEM, 
            output, 
            esri_pntr=False, 
            callback=default_callback
            )
        return output
    
    def d8_flow_accumulation(self)-> os.path:
        '''
        @DEM: Filled DEM raster.
        @Output: d8_flow Accumulation raster from a filled DEM.
        '''
        d8FAccOutput = addSubstringToName(self.FilledDEM,"_d8fllowAcc" ) 
        wbt.d8_flow_accumulation(
            self.FilledDEM, 
            d8FAccOutput, 
            out_type="cells", 
            log=False, 
            clip=False, 
            pntr=False, 
            esri_pntr=False, 
            callback=default_callback
            ) 
        return d8FAccOutput
    
    def jensonPourPoints(self,inOutlest,streams)-> os.path:
        '''
        Replace the points in the @inOutlet to the nearest stream. 
        @inOutlet: vector(point), Containig the point/s(outlet) to be replaced.
        @streams: raster: River network to take as reference.
        @output: Output vector file.
        @snap_dist	Maximum snap distance in map units (default = 15.0). Distance as radius search area. 
        '''
        jensonOutput = addSubstringToName(inOutlest,"_JensonPoint")
        wbt.jenson_snap_pour_points(
            inOutlest, 
            streams, 
            jensonOutput, 
            snap_dist = 15.0, 
            callback=default_callback
            )
        print("jensonPourPoints Done")
        return jensonOutput

    def watershedConputing(self,d8Pointer, jensonOutput)-> os.path:  
        output = addSubstringToName(self.FilledDEM, "_watersheds")
        wbt.watershed(
            d8Pointer, 
            jensonOutput, 
            output, 
            esri_pntr=False, 
            callback=default_callback
        )
        print("watershedConputing Done")
        return output

    def watershedHillslopes(self,d8Pointer, streams)-> os.path:  
        output = addSubstringToName(self.FilledDEM, "_hillslope")
        wbt.hillslopes(
            d8Pointer, 
            streams, 
            output, 
            esri_pntr=False, 
            callback=default_callback
        )
        return output

    def DInfFlowAcc(self, inD8Pointer, log = False)-> os.path:
        ''' 
        Compute DInfinity flow accumulation algorithm.
        Ref: https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#dinfflowaccumulation  
        We keep the DEFAULT SETTING  from source, which compute "Specific Contributing Area". 
        See ref for the description of more output’s options. 
        @Argument: 
            @inD8Pointer: D8-Pointer raster
            @log (Boolean): Apply Log-transformation on the output raster
        @Output: 
            DInfFlowAcculation map. 
        '''
        output = addSubstringToName(self.FilledDEM,"_dInfFAcc")
        wbt.d_inf_flow_accumulation(
            inD8Pointer, 
            output, 
            out_type="Specific Contributing Area", 
            threshold=None, 
            log=log, 
            clip=False, 
            pntr=True, 
            callback=default_callback
            )
        return output
   
    def extract_stream(self,FAcc,threshold:float = None)->os.path:
        '''
        "This tool can be used to extract, or map, the likely stream cells from an input flow-accumulation image "
        ref: https://www.whiteboxgeo.com/manual/wbt_book/available_tools/stream_network_analysis.html?highlight=stream%20network%20analyse#ExtractStreams
        If the threshold is not provided, the value is compute as a percent (95% default) of the maximum flow accumulation value.
        
        @FAcc: Raster flow accumulation map.
        @threshold: Number of cells or area to be consider to start and mantain a channel.
        @output: Path to river network raster map 
        '''
        output = addSubstringToName(self.FilledDEM,'_stream')
        if not threshold:
            Quant = computeRasterQuantiles(FAcc)
            print(f" The FAcc quantiles are_______ {Quant}")
            threshold = Quant[1] ### All values greater than the 75% of Flow Acc map. 
            print(f" The FAcc threshold is_______ {threshold}")
        wbt.extract_streams(
            FAcc, 
            output, 
            threshold, 
            zero_background=False, 
            callback=default_callback
        )
        return output

    def computeStrahlerOrder(self,d8_pointer, streamRaster)-> os.path:
        '''
        @Input: raster D8 pointer file
        @streams: Input raster streams file
            @esri_pntr	D8 pointer uses the ESRI style scheme
            @zero_background	Flag indicating whether a background value of zero should be used
        @output	Output raster file
        '''
        output = addSubstringToName(self.FilledDEM,'_StrahOrd')
        wbt.strahler_stream_order(
            d8_pointer, 
            streamRaster, 
            output, 
            esri_pntr=False, 
            zero_background=False, 
            callback=default_callback
        )
        return output

    def thresholdingStrahlerOrders(self, strahlerOrderRaster, maxStrahOrder:int=4) ->os.path:
        '''
        Extract the desired numer of strahler orders. 
        @strahlerOrderRaster
        @maxStrahOrder: Max numper of strahler order to be returned, starting from max and decresing.
        @return: raster of the same type of StrahlerOrder, with values 0-1. 1- river cells, 0-no river cells.
        ex. 
            StrahlerOrder raster input has values 5,6,7,8,9,10,11,12. 
            maxStrahOrder = 4, 
            return raster with 1 in all cell with strahler orders [12,11,10,9], zero otherwhise.  
        '''
        _,max = computeRasterMinMax(strahlerOrderRaster)
        threshold = int(max-maxStrahOrder) # MainRIver are the last <limit> numbers of Strahler Orders
        print(f'Max Satrahler order = {max}. For main river considered {threshold} to {max}')
        validStrahler_statement = str("'"+strahlerOrderRaster+"'"+'>='+str(threshold)) 
        #####  Get Max strahler order
        mainRiverPath = addSubstringToName(self.DEMName,'_mainRiver')
        self.rasterCalculator(mainRiverPath,validStrahler_statement)
        # Get the maximum value
        return mainRiverPath

    def WbT_HAND(self,streams)-> os.path:
        '''
        This function requires a filled DEM as input. 
        @DEM: raster: Filled DEM.
        @stream: Input raster streams file
        @Output: Output raster path file
        '''
        output = addSubstringToName(self.FilledDEM,'_HAND')
        wbt.elevation_above_stream(
            self.FilledDEM, 
            streams, 
            output,
            callback=default_callback
        )
        return output
        
    def WbT_HAND_euclidean(self,streams)-> os.path:
        '''
        Compute the elevation as the euclidian distance from the river to each cell.
        ref: https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#elevationabovestreameuclidean
        
        This function requires a filled DEM as input. 
        @DEM: raster: Filled DEM.
        @stream: Input raster streams file
        @Output: Output raster path file
        '''
        output = addSubstringToName(self.FilledDEM,'_WbT_HANDEuc')
        wbt.elevation_above_stream_euclidean(
            self.FilledDEM, 
            streams, 
            output,
            callback=default_callback
        )
        return output

    def wbT_geomorphons(self)->os.path:
        '''
        Compute geomorpohones according:
        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/geomorphometric_analysis.html?highlight=geomorphons#geomorphons
        The output is a 10 classes geomorphons.
        1	Flat
        2	Peak (summit)
        3	Ridge
        4	Shoulder
        5	Spur (convex)
        6	Slope
        7	Hollow (concave)
        8	Footslope
        9	Valley
        10	Pit (depression)
        @dem: Input raster DEM file
        @output: Output raster file
        @search: Look up distance (in cells)
        @threshold:	Flatness threshold for the classification function (in degrees)
        @fdist: Distance (in cells) to begin reducing the flatness @threshold: to avoid problems with pseudo-flat lines-of-sight
        @skip: Distance (in cells) to begin calculating lines-of-sight. (Default 1 for a DEM of 16m x 16m cell size).
        @forms:	Classify geomorphons into 10 common land morphologies, else output ternary pattern
        @residuals:	Convert elevation to residuals of a linear model
        '''
        output = addSubstringToName(self.DEMName, '_GMorph')
        wbt.geomorphons(
            self.DEMName, 
            output, 
            search=50, 
            threshold=0.0, 
            fdist=0, 
            skip=1, 
            forms=True, 
            residuals=False, 
            callback=default_callback
        )
        return output

    def FloodOrder(self,)-> os.path:
        ''' 
        
        '''
        output = addSubstringToName(self.DEMName,"_FloodOrd")
        wbt.flood_order(
            self.DEMName, 
            output, 
            callback=default_callback
            )
        return output
 
    def euclideanDistance(self,objectiveRaster)->os.path:
        '''
        "This tool will estimate the Euclidean distance (i.e. straight-line distance) between each grid cell and the nearest 'target cell' in the input image. TARGET cells are ALL NON-ZERO AND ALL NON-NODATA grid cells. Distance in the output image is measured in the same units as the horizontal units of the input image." 
        ref: https://www.whiteboxgeo.com/manual/wbt_book/available_tools/gis_analysis_distance_tools.html?highlight=euclid#euclideandistance
        @objectiveRaster: Input raster with the 
        @output: Output raster filePath
        '''
        output = addSubstringToName(objectiveRaster, '_EucDist')  ## This intend to be the equivalent of GDAL.proximity() functino.
        wbt.euclidean_distance(
            objectiveRaster, 
            output, 
            callback=default_callback
            )
        return output

    def computeRasterHistogram(self,inRaster)-> os.path:
        '''
        For details see Whitebox Tools references at:
        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/mathand_stats_tools.html?#RasterHistogram
        @return: An *.html file with the computed histogram. The file is autoloaded. 
        '''
        output = addSubstringToName(inRaster,'_histogram')
        output = replaceExtention(output, '.html')
        wbt.raster_histogram(
            inRaster, 
            output, 
            callback=default_callback
            )   
        return output

    def rasterCalculator(self, output, statement:str)-> os.path:
        '''
        For details see Whitebox Tools references at:
        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/mathand_stats_tools.html#RasterCalculator
        
        @statement : string of desired opperation. Raster must be cuoted inside the statement str. ex "'raster1.tif' - 'rater2.tif'"
        '''
        wbt.raster_calculator(
            output, 
            statement, 
            callback=default_callback
            )
        return output
    
    def get_WorkingDir(self):
        return str(self.workingDir)
    
    def set_WorkingDir(self,NewWDir):
        wbt.set_working_dir(NewWDir)

class generalRasterTools():
    def __init__(self, workingDir):
        if os.path.isdir(workingDir): # Creates output dir, if it does not already exist. 
            self.workingDir = workingDir
            wbt.set_working_dir(workingDir)
        else:
            self.workingDir = input('Enter working directory')
            ensureDirectory(self.workingDir)
            wbt.set_working_dir(self.workingDir)
        # print('Current working directory : ', self.workingDir)
    
    def computeMosaic(self, outpouFileName:str):
        '''
        Compute wbt.mosaic across all .tif files into the workingDir.  
        @return: Return True if mosaic succeed, False otherwise. Result is saved to wbt.work_dir. 
        Argument
        @verifiedOutpouFileName: The output file name. IMPORTANT: include the "*.tif" extention.
        '''
        verifiedOutpouFileName = checkTifExtention(outpouFileName)
        outFilePathAndName = os.path.join(wbt.work_dir,verifiedOutpouFileName)
        if wbt.mosaic(
            output=outFilePathAndName, 
            method = "nn"  # Calls mosaic tool with nearest neighbour as the resampling method ("nn")
            ) != 0:
            print('ERROR running mosaic')  # Non-zero returns indicate an error.
            return False 
        return True

    def rasterResampler(sefl,inputRaster, outputRaster, outputCellSize:int,resampleMethod = 'bilinear'):
        '''
        wbt.Resampler ref: https://www.whiteboxgeo.com/manual/wbt_book/available_tools/image_processing_tools.html#Resample
        NOTE: It performes Mosaic if several inputs are provided, in addition to resampling. See refference for details. 
        @arguments: inputRaster, resampledRaster, outputCellSize:int, resampleMethod:str
        Resampling method; options include 'nn' (nearest neighbour), 'bilinear', and 'cc' (cubic convolution)
        '''
        verifiedOutpouFileName = checkTifExtention(outputRaster)
        outputFilePathAndName = os.path.join(wbt.work_dir,verifiedOutpouFileName)
        if isinstance(inputRaster, list):
            inputs = sefl.prepareInputForResampler(inputRaster)
        else: 
            inputs = inputRaster        
        wbt.resample(
            inputs, 
            outputFilePathAndName, 
            cell_size=outputCellSize, 
            base=None, 
            method= resampleMethod, 
            callback=default_callback
            )
        return outputFilePathAndName
     
    def mosaikAndResamplingFromCSV(self,csvName, outputResolution:int, csvColumn:str, clearTransitDir = True):
        '''
        Just to make things easier, this function download from *csv with list of dtm_url,
         do mosaik and resampling at once. 
        NOTE: If only one DEM is provided, mosaik is not applyed. 
        Steps:
        1- create TransitFolder
        2- For *.csv in the nameList:
             - create destination Folder with csv name. 
             - import DEM into TransitFolder
             - mosaik DEM in TransitFoldes if more than one is downloaded.
             - resample mosaik to <outputResolution> argument
             - clear TransitFolder
        '''
        ## Preparing for download
        transitFolderPath = createTransitFolder(self.workingDir)
        sourcePath_dtm_ftp = os.path.join(self.workingDir, csvName) 
        name,ext = splitFilenameAndExtention(csvName)
        print('filename :', name, ' ext: ',ext)
        destinationFolder = makePath(self.workingDir,name)
        ensureDirectory(destinationFolder)
        dtmFtpList = createListFromCSVColumn(sourcePath_dtm_ftp,csvColumn)
        
        ## Download tails to transit folder
        downloadTailsToLocalDir(dtmFtpList,transitFolderPath)
        savedWDir = self.workingDir
        resamplerOutput = makePath(destinationFolder,(name +'_'+str(outputResolution)+'m.tif'))
        resamplerOutput_CRS_OK = makePath(destinationFolder,(name +'_'+str(outputResolution)+'m.tif'))
        wbt.set_working_dir(transitFolderPath)
        
        ## recover all downloaded *.tif files path
        dtmTail = listFreeFilesInDirByExt(transitFolderPath, ext = '.tif')
        crs,_ = self.get_CRSAndTranslation_GTIFF(dtmFtpList[0])
        
        ## Merging tiles and resampling
        self.rasterResampler(dtmTail,resamplerOutput,outputResolution)
        self.set_CRS_GTIF(resamplerOutput, resamplerOutput_CRS_OK, crs)
        wbt.set_working_dir(savedWDir)
        
        ## Celaning transit folder. 
        if clearTransitDir: 
            clearTransitFolderContent(transitFolderPath)

    def rasterToVectorLine(sefl, inputRaster, outputVector):
        wbt.raster_to_vector_lines(
            inputRaster, 
            outputVector, 
            callback=default_callback
            )

    def rasterVisibility_index(sefl, inputDTM, outputVisIdx, resFator = 2.0):
        '''
        Both, input and output are raster. 
        '''
        wbt.visibility_index(
                inputDTM, 
                outputVisIdx, 
                height=2.0, 
                res_factor=resFator, 
                callback=default_callback
                )           

    def gaussianFilter(sefl, input, output, sigma = 0.75):
        '''
        input@: kernelSize = integer or tupel(x,y). If integer, kernel is square, othewise, is a (with=x,hight=y) rectagle. 
        '''
        wbt.gaussian_filter(
        input, 
        output, 
        sigma = sigma, 
        callback=default_callback
        )
    
    def prepareInputForResampler(self,nameList):
        inputStr = ''   
        if len(nameList)>1:
            for i in range(len(nameList)-1):
                inputStr += nameList[i]+';'
            inputStr += nameList[-1]
            return inputStr
        return str(*nameList)

    def get_CRSAndTranslation_GTIFF(self,input_gtif):
        '''
         @input_gtif = "path/to/input.tif"
         NOTE: Accept URL as input. 
        '''
        with rio.open(input_gtif) as src:
        # Extract spatial metadata
            input_crs = src.crs
            input_gtif  = src.transform
            src.close()
            return input_crs, input_gtif  

    def set_CRS_GTIF(self,input_gtif, output_tif, in_crs):
        arr, kwds = self.separate_array_profile(input_gtif)
        kwds.update(crs=in_crs)
        with rio.open(output_tif,'w', **kwds) as output:
            output.write(arr)
        return output_tif

    def set_Tanslation_GTIF(self, input_gtif, output_tif, in_gt):
        arr, kwds = self.separate_array_profile(input_gtif)
        kwds.update(transform=in_gt)
        with rio.open(output_tif,'w', **kwds) as output:
            output.write(arr)
        return output_tif

    def separate_array_profile(self, input_gtif):
        with rio.open(input_gtif) as src: 
            profile = src.profile
            # print('This is a profile :', profile)
            arr = src.read()
            src.close() 
        return arr, profile

    def ensureTranslationResolution(self, rioTransf:rio.Affine, desiredResolution: int):
        '''
        NOTE: For now it works for square pixels ONLY!!
        Compare the translation values for X and Y transformation with @desiredResolution. 
        If different, the values are replaced by the desired one. 
        return:
         @rioAfine:rio.profiles with the new resolution
        '''
        if rioTransf[0] != desiredResolution:
            newTrans = rio.Affine(desiredResolution,
                                rioTransf[1],
                                rioTransf[2],
                                rioTransf[3],
                                -1*desiredResolution,
                                rioTransf[5])
        return newTrans

    def get_rasterResolution(self, inRaster):
        with rio.open(inRaster) as src:
            profile = src.profile
            transformation = profile['transform']
            res = int(transformation[0])
        return res
    
    def get_WorkingDir(self):
        return str(self.workingDir)
    
    def setWBTWorkingDir(self, workingDir):
        wbt.set_working_dir(workingDir)

def DEMFeaturingForMLP_WbT(DEM)-> list:
    '''
    The goal of this function is to compute all necesary(or desired) maps for MLP classification inputs, starting from a DEM. The function use WhiteboxTools library. All output adress are managed into the class WbT_DEM_FeatureExtraction(). Also the WbT_working directory is setted at the same parent dir of the input DEM. 
    The steps are (See function description formmore details.):
    1- DEM correction <fixNoDataAndfillDTM()>
    2- Compute geomorphons in DEM
    3- Compute Flood Order in DEM
    4- Fill DEM with wang_and_liu method
    5- Slope in corrected DEM
    6- Compute flow direction <D8_pointe()>
    7- Compute Flow accumulation <DInfFlowAcc()>
    8- Extract stream.
    9- Compute stream order with Strahler Order.
    10- Extract main stream.
    11- Compute HAND.
    12 -Compute subcatchment with <watershedHillslopes>
    13- Compute distance to stream.(Proximity)

    @DEM: Digital elevation mode raster.
    @Return: A list of some produced maps. The maps to be added to a multiband *.tif.
    
    NOTE: Also save a list of produced features in a csv file for further automation process. 
    '''
    outList = [DEM]
    DEM_Features = WbT_DEM_FeatureExtraction(DEM)
    print(f"Extracting features from DEM >>>>")
    ## Geomorphons
    geomorph = DEM_Features.wbT_geomorphons()
    replace_no_data_value(geomorph)
    outList.append(geomorph)
    print(f"-------------Geomorphons ready at {geomorph}")
    ## Flood Order
    FloodOrd = DEM_Features.FloodOrder()
    replace_no_data_value(FloodOrd)
    outList.append(FloodOrd)
    print(f"-------------Flood Order ready at {FloodOrd}")
    ## DEM Filling
    DEM_Features.fixNoDataAndfillDTM()
    print(f"-------------DEM corrected ready at {DEM_Features.FilledDEM}")
    ## Slope
    slope = DEM_Features.computeSlope()
    outList.append(slope)
    print(f"-------------Slope ready at {slope}")
    ## Flow direction
    D8Pointer = DEM_Features.d8_Pointer() 
    print(f"-------------Flow direction ready at {D8Pointer}")
    FAcc = DEM_Features.d8_flow_accumulation()
    replace_no_data_value(FAcc)
    outList.append(FAcc)
    print(f"-------------Flow accumulation ready at {FAcc}")
    stream = DEM_Features.extract_stream(FAcc)
    print(f"-------------Stream ready at {stream}")
    strahlerOrder = DEM_Features.computeStrahlerOrder(D8Pointer,stream)
    print(f"-------------Strahler Order ready at {strahlerOrder}")
    mainRiver = DEM_Features.thresholdingStrahlerOrders(strahlerOrder, maxStrahOrder=3)
    print(f"-------------Main river ready at {mainRiver}")
    HAND = DEM_Features.WbT_HAND(mainRiver)
    outList.append(HAND)
    print(f"-------------HAND index ready at {HAND}")
    proximity = computeProximity(mainRiver)
    outList.append(proximity)
    print(f"-------------Proximity index ready at {proximity}")
    ## Catchment extraction
    DEM_Features.watershedHillslopes(D8Pointer,mainRiver)
    ### Save the list of features path as csv. 
    csvPath = replaceExtention(DEM,'_FeaturesPathList.csv')
    createCSVFromList(csvPath,outList)
    print(f"--------Features done!----------")
    return outList  

# Helpers
def checkTifExtention(fileName):
    if ".tif" not in fileName:
        newFileName = input("enter a valid file name with the '.tif' extention")
        return newFileName
    else:
        return fileName

def downloadTailsToLocalDir(tail_URL_NamesList, localPath):
    '''
    Import the tails in the url <tail_URL_NamesList>, 
        to the local directory defined in <localPath>.
    '''
    confirmedLocalPath = ensureDirectory(localPath)
    for url in tail_URL_NamesList:
        download_url(url, confirmedLocalPath)
    print(f"Tails downloaded to: {confirmedLocalPath}")

##################################################################
########  DATA Analis tools for Geo Spatial information   ########
##################################################################

def remove_nan_vector(array):
    nan_indices = np.where(np.isnan(array))
    cleaned_array = np.delete(array, nan_indices)
    return cleaned_array

def remove_nan(array):
    nan_indices = np.where(np.isnan(array).any(axis=1))[0]
    cleaned_array = np.delete(array, nan_indices, axis=0)
    return cleaned_array

def plotRasterPDFComparison(DEMList:list,title:str='Raster PDF', ax_x_units:str='', bins:int = 100, addmax= False, show:bool=False, save:bool=False, savePath:str='', plotGlobal:bool=False):
    '''
    # this create the kernel, given an array, it will estimate the probability over that values
    kde = gaussian_kde( data )
    # these are the values over which your kernel will be evaluated
    dist_space = linspace( min(data), max(data), 100 )
    # plot the results
    plt.plot( dist_space, kde(dist_space))
    @DEMList:list,
    @title:str='RasterPDF' 
    @ax_x_units:str='' 
    @bins:int = 100 
    @addmax= False
    @show:bool=False 
    @globalMax:int = 0 
    @save:bool=True 
    @savePath:str=''
    ''' 
    global_Min = np.inf
    global_Max = -np.inf
    nameList = []
    fullDataSet = np.array([], dtype=np.float32)
    
    ### Prepare plot
    fig, ax = plt.subplots(1,sharey=True, sharex=True, tight_layout=True)
    colors = plt.cm.jet(np.linspace(0, 1, 2*len(DEMList)+5))# 
    '''
    turbo; jet; nipy_spectral;gist_ncar;gist_rainbow;rainbow, brg
    '''
    colorIdx = 0
    for dem in DEMList:
        _,demName,_ = get_parenPath_name_ext(dem)
        # if "Ottawa" in demName or 'Hamilton' in demName or "AL" in demName:
        dem = replaceRastNoDataWithNan(dem,extraNoDataVal=-9999)
        dataRechaped = np.reshape(dem,(-1))
        data= remove_nan_vector(dataRechaped)
        dataMin =  np.min(data)
        relativeElevation = np.subtract(data,dataMin)
        fullDataSet = np.concatenate((fullDataSet,relativeElevation))
        print(f'FullDataset shape {fullDataSet.shape}')
        print(f'data shape {relativeElevation.shape}')
        dataMin =  np.min(relativeElevation)
        dataMax = np.max(relativeElevation)
        global_Min = np.minimum(global_Min,dataMin)
        global_Max = np.maximum(global_Max,dataMax)

        ## If <bins> is a list, add the maximum value to <bins>.  
        if (addmax and isinstance(bins,list)):
            bins.append(global_Max).astype(int)
        print(f'______________ {demName} ____________')
        # nameList.append(demName)
        # counts, bins = np.histogram(relativeElevation, bins= 200)
        # bin_centers = 0.5 * (bins[:-1] + bins[1:])
        # ax.plot(bin_centers, counts,color=colors[colorIdx],linewidth=0.8)
        colorIdx+=2
        
        
    # ## Plot global PDF
    counts, bins = np.histogram(fullDataSet, bins= 400)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    ax.plot(bin_centers, counts,color='k',linewidth=0.9)
    # nameList.append('Global histogram')
    
    ## Complet plot space
    ax.legend(['Relative elevation'], prop={'size': 5})
    ax.set_title(title)
    ax.set_xlabel(ax_x_units) 
    ax.set_ylabel('Frequency')
   
    if isinstance(bins,list):
        plt.xticks(bins)
        print(bins)
        plt.gca().set_xticklabels([str(i) for i in bins], minor = True)
          
    if save:
        if not savePath:
            savePath = os.path.join(os.getcwd(),title +'.png')
            print(f'Figure: {title} saved to dir: {savePath}')
        plt.savefig(savePath)
    
    if show:
        plt.show()

def addCollFromRasterToDataFrame(df_In,map, colName:str='')->pd.DataFrame:
    '''
    Add a column to a dataset, sampling from a raster at the points defined in the x_coord and y_coord of the input dataframe.
    @df_In: pandas DataFrame with the two first colums being: x_coord,y_coord.
    @map: Raster map. Raster map expected to have only one layer. 
    @colName: Name to asigne to the new column.If empty, the new column will be the map prefix. 
    @return: A dataframe with a column containing the sampling from <map>. 
    '''
    xyCols = df_In.iloc[:, :2].values
    newColValues = getRasterSampleFromPoint(map,xyCols)
    df_out = df_In.copy() 
    if colName:
        df_out[colName]=newColValues
    else:
        _,tifName,_ = get_parenPath_name_ext(map)
        colName = tifName.split("_")[-1]
        df_out[colName]=newColValues
    return df_out

def addCollFromVectorFieldToDataFrame(df_In,vector, field, colName:str='')->pd.DataFrame:
    '''
    Add a column to a dataset, sampling from a raster at the points defined in the x_coord and y_coord of the input dataframe.
    @df_In: pandas DataFrame with the two first colums being: x_coord,y_coord.
    @map: Raster map. Raster map expected to have only one layer. 
    @colName: Name to asigne to the new column.If empty, the new column will be the map prefix. 
    @return: A dataframe with a column containing the sampling from <map>. 
    '''
    xyCols = df_In.iloc[:, :2].values
    vector = ogr.Open(vector_path)
    layer = vector.GetLayer()
    newColValues = getFieldValueFromPolygon(vector,field,xyCols)
    df_out = df_In.copy() 
    
    
    if colName:
        df_out[colName]=newColValues
    else:
        _,tifName,_ = get_parenPath_name_ext(map)
        colName = tifName.split("_")[-1]
        df_out[colName]=newColValues
    return df_out


######    NOTES   #####
'''
list of the built-in color maps in Matplotlib:

**Perceptually Uniform Sequential**: `viridis`, `plasma`, `inferno`, `magma`, `cividis`

**Sequential**: `Greys`, `Purples`, `Blues`, `Greens`, `Oranges`, `Reds`, `YlOrBr`, `YlOrRd`, `OrRd`, `PuRd`, `RdPu`, `BuPu`, `GnBu`, `PuBu`, `YlGnBu`, `PuBuGn`, `BuGn`, and `YlGn`

**Sequential (2)**: `binary`, `gist_yarg`, `gist_gray`, `gray`, `bone`, `pink`, `spring`, `summer`, `autumn`, `winter`, `cool`, `Wistia`, `hot`, `afmhot`,`gist_heat`,`copper`

**Diverging**:  `PiYG`,`PRGn`,`BrBG`,`PuOr`,`RdGy`,`RdBu`,`RdYlBu`,`RdYlGn`,`Spectral`,`coolwarm`,`bwr`,`seismic`

**Cyclic**:  `twilight`,`twilight_shifted`,`hsv`

**Qualitative**:  `Pastel1`,`Pastel2`,`Paired`,`Accent`,`Dark2`,`Set1`,`Set2`,`Set3`,`tab10`,`tab20`,`tab20b`,`tab20c`


'''

def read_shapefile(gdf:gpd.GeoDataFrame, field_name, x, y)-> [np.array,list]:
    '''
    ## To read the shapefile into a geopandas dataframe
    gdf = gpd.read_file(file_path)
    '''
    # extract the feature values from the dataframe
    feature_values = gdf.loc[(gdf.geometry.x == x) & (gdf.geometry.y == y), field_name].values
    # return the feature values as an array
    return feature_values

def sampleUniqueValByField_shpfile(shapefile_path, field_name:str, coordinates)->[np.ndarray,list]:
    '''
    Sample a shapefile from a list of <coordinates> and return: a column per unique value in the <field_name> and a list of unique values as string.
    NOTE: The function have been created to sample flood labels polygons by classes for the flood modeling project. 
    @shapefile_path: os.path: Path to the shapefile
    @field_name: str: name of the field of interest in the shapefile. MUST be a unique fiel, DO NOT accept list for now. 
    @coordinates: np.array: array of shape (n,2), with n pairs like <x_coord,y_coord>.
    @Return: 
        values: ndarray: Array of shape (n,NumberOFUniqueValues).
        featuresID: list: list of unique values in the <field_name>. 
    '''
    # Open the shapefile
    shapefile = ogr.Open(shapefile_path)
    layer = shapefile.GetLayer()
    featureCount = layer.GetFeatureCount()
    featuresID = []
    ### Collect features IDs from the shpfile. 
    for i in range(featureCount):
        feature = layer.GetFeature(i)
        next_ID = str(int(feature.GetField(field_name)))
        print(f'Feature ID {next_ID}')
        if next_ID not in featuresID:
            featuresID.append(next_ID)
    
    # Create an empty array to store the values
    values = np.zeros((coordinates.shape[0],featureCount))
    print(f'Output array shape {values.shape}')
    # Iterate over each pair of coordinates
    row = 0
    for x, y in coordinates:
        # Create a point
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
        layer.SetSpatialFilter(point)
        # Iterate over each feature in the shapefile
        for feature in layer:
            fid = str(int(feature.GetField(field_name)))
            values[row,featuresID.index(fid)] = feature.GetField(field_name)
            # print(f'x->{x}, y->{y}, fid -> {fid}, value -> {feature.GetField(field_name)}')
        point = None
        row +=1
    return values,featuresID

def addTargetColsToDataFrameCSV(df_csv,shpFile,target:str ='percentage', excludeClass:list=['0']):
    '''
    This function add to a dataset the Target columns. The dataset is provided as *.csv file and save to the same path a new file with perfix = "_withClasses.csv"
    @df_csv: os.path: Path to the *csv file.
    @shpFile: os.path: Path to the shapefile to sample from.
    @target:str = target coll name in the dataset.
    @return: os.path: path to the new *csv containing the dataset. 
    '''
    # Read the csv as pd.DataFrame
    df = pd.read_csv(df_csv)
    # df.drop('0', axis=1, inplace=True)
    ## Extract x,y pairs array.
    xy = df.iloc[:,:2].values
    # Sample unique values by coordinates
    array, nameList = sampleUniqueValByField_shpfile(shpFile,target,xy)
    # Add colls to the dataframe and save it.
    for name in nameList:
        if name not in excludeClass: 
            df[name] = array[:,nameList.index(name)]
    saveTo = addSubstringToName(df_csv,"_withClasses")
    print(df.head)
    df.to_csv(saveTo,index=None)
    return saveTo 