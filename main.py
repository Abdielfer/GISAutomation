# import dc_extract
import dc_extract.describe.describe as d
from dc_extract.extract_cog import extract_cog as exc
import hydra 
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf
import util as U
import logging

def dc_describe(cfg: DictConfig):
    '''
    Configurate the call of the d.describe() with hydra parameters.
    '''
    instantiate(OmegaConf.create(cfg.parameters['describeCollections']))
    return True

def dc_serach(cfg: DictConfig):
    '''
    Configurate the call of the d.search()  with hydra parameters.
    '''
    out = instantiate(OmegaConf.create(cfg.parameters['dc_search']))
    return out

def dc_extraction(cfg: DictConfig):
    '''
    Configurate the call of extract_cog() with hydra parameters.
    '''
    out = instantiate(OmegaConf.create(cfg.parameters['dc_extrac_cog']))
    return out

def logger(cfg: DictConfig, nameByTime):
    '''
    You can log all you want here!
    '''
    logging.info(f"Excecution number: {nameByTime}")
    logging.info(f"Output directory :{cfg['output_dir']}")
    logging.info(f"dc_search inputs: {cfg.parameters.dc_search}")
    logging.info(f"dc_description inputs: {cfg.parameters.dc_description}")
    logging.info(f"dc_extract inputs: {cfg.parameters.dc_extrac_cog}")

@hydra.main(version_base=None, config_path=f"config", config_name="mainConfigPC")
def main(cfg: DictConfig):
    nameByTime = U.makeNameByTime()
    logger(cfg,nameByTime)
    dc_describe(cfg)
    se = dc_serach(cfg)
    logging.info(f"Search output path: {se}")
    print(f"Search-->{se}")
    ex = dc_extraction(cfg)
    logging.info(f"Extraction output path: {ex}")
    print(f"Extraction -->{ex}")

if __name__ == "__main__":
    with U.timeit():
        main()  
