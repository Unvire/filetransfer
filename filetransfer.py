import json
import logging
from logging.handlers import RotatingFileHandler
import sys
from threading import Timer
import time
import os
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def __init__(self, sourcePath, commonDestinationPath, baseDestinaton, baseFolderPath):
        self.sourcePath = sourcePath
        self.commonDestinationPath = commonDestinationPath
        self.baseDesinationPath = baseDestinaton
        self.baseFolderPath = baseFolderPath
        self.enable = False

    def enableSet(self, state):
        # setter for enabling logging
        if self.enable and not state:
            logger.warning(f'Stopped logging on station {self.sourcePath}')
        if not self.enable and state:
            logger.warning(f'Started logging on station {self.sourcePath}')
        self.enable = state

    def on_any_event(self, event):
        if not self.enable:
            return
        
        if event.is_directory:
            return
        
        if event.event_type == 'created':
            logger.info(f"File created: {self.get_relative_path(event.src_path)}")
            time.sleep(1)
            self.copy_file(event)
        elif event.event_type == 'modified':
            logger.info(f"File modified: {self.get_relative_path(event.src_path)}")
            self.copy_file(event)
        elif event.event_type == 'moved':
            logger.info(f"File renamed: {self.get_relative_path(event.src_path)}")
            self.copy_file(event)
        elif event.event_type == 'deleted':
            logger.info(f"File deleted: {self.get_relative_path(event.src_path)}")

    # Get relative path starting from baseFolderPath
    def get_relative_path(self, path):
        return os.path.relpath(path, self.baseFolderPath)
    
    # Copy file to commonDestination folder, creating relative paths
    def copy_file(self, event):
        if event.event_type == 'moved':
            sourceFile = event.commonDest_path
        else:
            sourceFile = event.src_path

        logger.info(self.get_relative_path(sourceFile))
        commonDestinationPath = os.path.join(self.commonDestinationPath)
        
        destinationPath = os.path.join(self.baseDesinationPath, self.get_relative_path(sourceFile))
        os.makedirs(os.path.dirname(destinationPath), 0o777, True)

        try:
            shutil.copy(sourceFile, commonDestinationPath)
            shutil.copy(sourceFile, destinationPath)
        except Exception as e:
            print(f"Error copying file: {e}")

class WatchersThread:
    def __init__(self, configFile):
        self.t = None
        self.stations = {}
        self.configFile = configFile

    # Load config file and submit Watchers
    def reloadConf(self):
        try:
            with open(self.configFile, 'r') as f:
                    config = json.load(f)                    
                    enableFileTransfer = config['enableFileTranfer']

                    # close script
                    if not enableFileTransfer:
                        logger.info('Filetransfer.py stopped')
                        sys.exit(1)

                    commonDest = config['commonDest']
                    baseDest = config['baseDest']
                    baseSource = config['baseSource']
                    sourcesList = config['sources']
                    updateTime = float(config['updateTime'])

                    ## check if commonDest and baseSource exist
                    if not os.path.isdir(commonDest):
                        logger.error(f"commonDestination folder {commonDest} not found")
                        sys.exit(1)
                    if not os.path.isdir(baseDest):
                        logger.error(f"Base folder {baseDest} not found")
                        sys.exit(1)
                    if not os.path.isdir(baseSource):
                        logger.error(f"Base folder {baseSource} not found")
                        sys.exit(1)
                    

        ## handle errors in JSON file
        except json.decoder.JSONDecodeError as e:
            logger.error(f'Could not properly read JSON file: {e}')
            sys.exit(1)
        except FileNotFoundError:
            logger.error(f'Config file {self.configFile} not found')
            sys.exit(1)
        except KeyError as e:
            logger.error(f'Key error in config file: {e}')
            sys.exit(1)

        return commonDest, baseDest, baseSource, sourcesList, updateTime
    
    def updateObservers(self, commonDest, baseDest, baseSource, sourcesList):
        ## handle each station
        for i, source in enumerate(sourcesList):
            # check for name
            try:
                groupName = source['name']
            except KeyError:
                logger.warning(f'No "name" key in {i} group')
                continue

            # check for source
            try:
                stationsList = source['stations']
            except KeyError:
                logger.warning(f'No "stations" key in {i} group')
                continue

            # check for enable state
            try:
                enable = source['enable']
            except KeyError:
                enable = False
                logger.warning(f'No "enable" key for source: "{source}". Used false as a value')
            
            ## create list of paths inside groups
            pathsList = [baseSource + os.sep + stationPath for stationPath in stationsList]
            
            ## add new station to self.stations dict; check if group was modified
            if groupName not in self.stations or len(pathsList) != len(self.stations[groupName]['stations']):
                self.stations[groupName] = {'enable': enable, 'stations':[]}
                for station in pathsList:
                    ## check if source path is a folder and if it exists
                    if not os.path.isdir(station):
                        logger.error(f"Folder {station} not found")
                        continue
                    
                    # create MyHandler and delegate to state setter
                    eventHandler = MyHandler(station, commonDest, baseDest, baseSource)
                    eventHandler.enableSet(enable)
                    eventHandler_enableSetDelegate = eventHandler.enableSet

                    ## add station to dictionary
                    observer = Observer()
                    self.stations[groupName]['stations'].append((observer, eventHandler_enableSetDelegate))     # [observer, pointer to enable logging]
                    observer.schedule(eventHandler, station, recursive=True)
                    observer.start()
            else:
                # unpack observer and refernece to setter of MyHandler
                stations = self.stations[groupName]['stations']
                for _, MyHandlerEnableDelegate in stations:
                    MyHandlerEnableDelegate(enable)
           
    def run(self):
        print("Check config file for for new folders")
        commonDest, baseDest, baseSource, sourcesList, updateTime = self.reloadConf()
        self.updateObservers(commonDest, baseDest, baseSource, sourcesList)
        self.t = Timer(updateTime, self.run)
        self.t.start()
        
    def start(self):
        self.run()

# Logger definition
def getLogger():
    name = 'filetransfer'
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    os.makedirs("./logs", 0o777, True)
    file_handler = RotatingFileHandler(f"./logs/{name}.txt", maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(filename)s](%(lineno)s): %(message)s'))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

    logger.info(f"Logger {name} created")

    return logger

if __name__ == '__main__':   
    # logger
    logger = getLogger()

    # Check parameters
    if len(sys.argv) != 2:
        logger.error("Usage: python filetransfer.py <configFile>")
        sys.exit(1)        
    configFile = sys.argv[1]
    #configFile = 'filetransfer.conf'

    thread = WatchersThread(configFile)
    thread.start()



