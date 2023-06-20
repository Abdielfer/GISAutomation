import os
import numpy as np
import util as U
from whitebox.whitebox_tools import WhiteboxTools, default_callback
import whitebox_workflows as wbw   
from torchgeo.datasets.utils import download_url
import rasterio as rst
from rasterio.crs import CRS

## LocalPaths and global variables: to be adapted to your needs ##
currentDirectory = os.getcwd()
wbt = WhiteboxTools()
wbt.set_working_dir(currentDirectory)
wbt.set_verbose_mode(True)
wbt.set_compress_rasters(True) # compress the rasters map. Just ones in the code is needed

## Pretraitment #
class dtmTransformer():
    '''
     This class contain some functions to generate geomorphological and hydrological features from DTM.
    Functions are mostly based on WhiteBoxTools libraries. For optimal functionality DTM’s most be high resolution, 
    ideally Lidar 1 m or < 2m. 
    '''
    def __init__(self, workingDir):
        self.mainFileName = " "
        if os.path.isdir(workingDir): # Creates output dir if it does not already exist 
            self.workingDir = workingDir
            wbt.set_working_dir(workingDir)
        else:
            self.workingDir = input('Enter working directory')
            U.ensureDirectory(self.workingDir)
            wbt.set_working_dir(self.workingDir)
        
    
    def fixNoDataAndfillDTM(self, inDTMName, eraseIntermediateRasters = True):
        '''
        Ref:   https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#filldepressions
        To ensure the quality of this process, this method execute several steep in sequence, following the Whitebox’s authors recommendation (For mor info see the above reference).
        Steps:
        1-	Correct no data values to be accepted for all operation. 
        2-	Fill gaps of no data.
        3-	Fill depressions.
        4-	Remove intermediary results to save storage space (Optionally you can keep it. See @Arguments).  
        @Argument: 
        -inDTMName: Input DTM name
        -eraseIntermediateRasters(default = False): Erase intermediate results to save storage space. 
        @Return: True if all process happened successfully, EROR messages otherwise. 
        @OUTPUT: DTM <filled_ inDTMName> Corrected DTM with wang_and_liu method. 
        '''
        dtmNoDataValueSetted = "noDataOK_"+inDTMName
        wbt.set_nodata_value(
            inDTMName, 
            dtmNoDataValueSetted, 
            back_value=0.0, 
            callback=default_callback
            )
        dtmMissingDataFilled = "correctedNoData_"+inDTMName
        wbt.fill_missing_data(
            dtmNoDataValueSetted, 
            dtmMissingDataFilled, 
            filter=11, 
            weight=2.0, 
            no_edges=True, 
            callback=default_callback
            )
        name,_ = U.splitFilenameAndExtention(inDTMName)

        output = name + "_filled.tif"
        wbt.fill_depressions_wang_and_liu(
            dtmMissingDataFilled, 
            output, 
            fix_flats=True, 
            flat_increment=None, 
            callback=default_callback
            )
        if eraseIntermediateRasters:
            try:
                os.remove(os.path.join(wbt.work_dir,dtmNoDataValueSetted))
                os.remove(os.path.join(wbt.work_dir,dtmMissingDataFilled))
            except OSError as error:
                print("There was an error removing intermediate results.")
        return True

    def d8FPointerRasterCalculation(self, inFilledDTMName):
        '''
        @argument:
         @inFilledDTMName: DTM without spurious point ar depression.  
        @UOTPUT: D8_pioter: Raster tu use as input for flow direction and flow accumulation calculations. 
        '''
        output = "d8Pointer_" + inFilledDTMName
        wbt.d8_pointer(
            inFilledDTMName, 
            output, 
            esri_pntr=False, 
            callback=default_callback
            )
    
    def d8_flow_accumulation(self, inFilledDTMName):
        d8FAccOutputName = "d8fllowAcc"+inFilledDTMName
        wbt.d8_flow_accumulation(
            inFilledDTMName, 
            d8FAccOutputName, 
            out_type="cells", 
            log=False, 
            clip=False, 
            pntr=False, 
            esri_pntr=False, 
            callback=default_callback
            ) 
            
    def dInfFlowAcc(self, inFilledDTMName, id,  userLog: bool):
        output = id
        wbt.d_inf_flow_accumulation(
            inFilledDTMName, 
            output, 
            out_type="ca", 
            threshold=None, 
            log=userLog, 
            clip=False, 
            pntr=False, 
            callback=default_callback
        )
  
    def jensePourPoint(self,inOutlest,d8FAccOutputName):
        jensenOutput = "correctedSnapPoints.shp"
        wbt.jenson_snap_pour_points(
            inOutlest, 
            d8FAccOutputName, 
            jensenOutput, 
            snap_dist = 15.0, 
            callback=default_callback
            )
        print("jensePourPoint Done")

    def watershedConputing(self,d8Pointer, jensenOutput):  
        output = "watersheds_" + d8Pointer
        wbt.watershed(
            d8Pointer, 
            jensenOutput, 
            output, 
            esri_pntr=False, 
            callback=default_callback
        )
        print("watershedConputing Done")

    def DInfFlowCalculation(self, inD8Pointer, log = False):
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
        output = "dInf_" + inD8Pointer
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

    ### Ready  ####
    def computeSlope(self,inDTMName,outSlope):
        wbt.slope(inDTMName,
                outSlope, 
                zfactor=None, 
                units="degrees", 
                callback=default_callback
                )
    
    def computeAspect(self,inDTMName):
        outAspect = 'aspect_'+ inDTMName
        wbt.aspect(inDTMName, 
                outAspect, 
                zfactor=None, 
                callback=default_callback
                )
    def get_WorkingDir(self):
        return str(self.workingDir)

class generalRasterTools():
    def __init__(self, workingDir):
        if os.path.isdir(workingDir): # Creates output dir, if it does not already exist. 
            self.workingDir = workingDir
            wbt.set_working_dir(workingDir)
        else:
            self.workingDir = input('Enter working directory')
            U.ensureDirectory(self.workingDir)
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
            inputs = generalRasterTools.prepareInputForResampler(inputRaster)
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
    def mosaikAndResamplingFromCSV(self,csvName, outputResolution: int, csvColumn:str, clearTransitDir = True):
        '''
        Just to make things easier, this function download from *csv with list of dtm_url,
         do mosaik and resampling at once. 
        NOTE: If only one DTM is provided, mosaik is not applyed. 
        Steps:
        1- create TransitFolder
        2- For *.csv in the nameList:
             - create destination Folder with csv name. 
             - import DTM into TransitFolder
             - mosaik DTM in TransitFoldes if more than is downloaded.
             - resample mosaik to <outputResolution> argument
             - clear TransitFolder
        '''
        transitFolderPath = U.createTransitFolder(self.workingDir)
        sourcePath_dtm_ftp = os.path.join(self.workingDir, csvName) 
        name,ext = U.splitFilenameAndExtention(csvName)
        print('filename :', name, ' ext: ',ext)
        destinationFolder = U.makePath(self.workingDir,name)
        U.ensureDirectory(destinationFolder)
        dtmFtpList = U.createListFromCSVColumn(sourcePath_dtm_ftp,csvColumn)
        downloadTailsToLocalDir(dtmFtpList,transitFolderPath)
        savedWDir = self.workingDir
        resamplerOutput = U.makePath(destinationFolder,(name +'_'+str(outputResolution)+'m.tif'))
        resamplerOutput_CRS_OK = U.makePath(destinationFolder,(name +'_'+str(outputResolution)+'m_CRS_OK.tif'))
        setWBTWorkingDir(transitFolderPath)
        dtmTail = U.listFreeFilesInDirByExt(transitFolderPath, ext = '.tif')
        crs,_ = generalRasterTools.get_CRSAndTranslation_GTIFF(self,dtmFtpList[0])
        generalRasterTools.rasterResampler(self,dtmTail,resamplerOutput,outputResolution)
        generalRasterTools.set_CRS_GTIF(self,resamplerOutput, resamplerOutput_CRS_OK, crs)
        setWBTWorkingDir(savedWDir)
        if clearTransitDir: 
            U.clearTransitFolderContent(transitFolderPath)

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
    
    def prepareInputForResampler(nameList):
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
        with rst.open(input_gtif) as src:
        # Extract spatial metadata
            input_crs = src.crs
            input_gt  = src.transform
            src.close()
            return input_crs, input_gt  

    def set_CRS_GTIF(self,input_gtif, output_tif, in_crs):
        arr, kwds = generalRasterTools.separate_array_profile(self, input_gtif)
        kwds.update(crs=in_crs)
        with rst.open(output_tif,'w', **kwds) as output:
            output.write(arr)
        return output_tif

    def set_Tanslation_GTIF(self, input_gtif, output_tif, in_gt):
        arr, kwds = generalRasterTools.separate_array_profile(self, input_gtif)
        kwds.update(transform=in_gt)
        with rst.open(output_tif,'w', **kwds) as output:
            output.write(arr)
        return output_tif

    def separate_array_profile(self, input_gtif):
        with rst.open(input_gtif) as src: 
            profile = src.profile
            print('This is a profile :', profile)
            arr = src.read()
            src.close() 
        return arr, profile

    def ensureTranslationResolution(self, rstTransf:rst.Affine, desiredResolution: int):
        '''
        NOTE: For now it works for square pixels ONLY!!
        Compare the translation values for X and Y transformation with @desiredResolution. 
        If different, the values are replaced by the desired one. 
        return:
         @rstAfine:rst.profiles with the new resolution
        '''
        if rstTransf[0] != desiredResolution:
            newTrans = rst.Affine(desiredResolution,
                                rstTransf[1],
                                rstTransf[2],
                                rstTransf[3],
                                -1*desiredResolution,
                                rstTransf[5])
        return newTrans

    def get_rasterResolution(self, inRaster):
        with rst.open(inRaster) as src:
            profile = src.profile
            transformation = profile['transform']
            res = int(transformation[0])
        return res
    
    def get_WorkingDir(self):
        return str(self.workingDir)



# Helpers
def setWBTWorkingDir(workingDir):
    wbt.set_working_dir(workingDir)

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
        confirmedLocalPath = U.ensureDirectory(localPath)
        for url in tail_URL_NamesList:
            download_url(url, confirmedLocalPath)
        print(f"Tails downloaded to: {confirmedLocalPath}")

#### Exceutable 
def main():
    wbe = wbw.WbEnvironment()
    print(wbe.version())
    
if __name__ == "__main__":
    main()