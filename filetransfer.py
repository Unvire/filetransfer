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
    def __init__(self, src_path, dest_path, src_base):
        self.src_path = src_path
        self.dest_path = dest_path
        self.src_base = src_base
        self.enable = False

    def enableSet(self, state):
        # setter for enabling logging
        if self.enable and not state:
            logger.warning(f'Stopped logging on station {self.src_path}')
        if not self.enable and state:
            logger.warning(f'Started logging on station {self.src_path}')
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

    # Get relative path starting from src_base
    def get_relative_path(self, path):
        return os.path.relpath(path, self.src_base)
    
    # Copy file to destination folder, creating relative paths
    def copy_file(self, event):
        if event.event_type == 'moved':
            src_file = event.dest_path
        else:
            src_file = event.src_path

        logger.info(self.get_relative_path(src_file))
        dest_file = os.path.join(self.dest_path, self.get_relative_path(src_file))

        os.makedirs(os.path.dirname(dest_file), 0o777, True)

        try:
            shutil.copyfile(src_file, dest_file)
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

                    dest = config['dest']
                    baseSource = config['baseSource']
                    sourcesList = config['sources']

                    ## check if dest and baseSource exist
                    if not os.path.isdir(dest):
                        logger.error(f"Destination folder {dest} not found")
                        sys.exit(1)
                    if not os.path.isdir(baseSource):
                        logger.error(f"Base folder {baseSource} not found")
                        sys.exit(1)

        ## handle errors in JSON file
        except json.decoder.JSONDecodeError as e: ## add here exceptions types
            logger.error(f'Could not properly read JSON file: {e}')
            sys.exit(1)
        except FileNotFoundError:
            logger.error(f'Config file {self.configFile} not found')
            sys.exit(1)

        return dest, baseSource, sourcesList
    
    def updateObservers(self, dest, baseSource, sourcesList):
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
            
            ## add new station to self.stations dict 
            if source not in self.stations:
                if os.path.isdir(source):
                    # create MyHandler and delegate to state setter
                    event_handler = MyHandler(source, dest, baseSource)
                    event_handler.enableSet(enable)
                    event_handler_enableSetDelegate = event_handler.enableSet

                    ## add station to dictionary
                    observer = Observer()
                    self.stations[source] = [observer, event_handler_enableSetDelegate]     # [observer, pointer to enable logging]
                    observer.schedule(event_handler, source, recursive=True)
                    observer.start()
                else:
                    logger.error(f"Folder {source} not found")
            else:
                # unpack observer and refernece to setter of MyHandler
                observer, MyHandlerEnableDelegate = self.stations[source]
                MyHandlerEnableDelegate(enable)
           
    def run(self):
        print("Check config file for for new folders")
        dest, baseSource, sourcesList = self.reloadConf()
        self.updateObservers(dest, baseSource, sourcesList)
        self.t = Timer(30.0, self.run) #60
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



