# FileTransfer
The purpose of this script is to monitor folders with log files from test machines and copy them to another location as soon as they are created/modified/deleted/renamed. 

# Config file

Description of config's file(JSON)  keys:
 - forceKillScript: bool -> raises exception that kills the script,
 - updateTime: int -> time that script waits between reloading the config file,
 - stopLoggingOnAllStations: bool -> if false then logging is disabled on all stations
 - commonDest: str -> (optinal parameter) path that the files are copied to (all files to one folder); use empty string to disable this feature
 - baseDest: str -> common path for all copied files (basePath -> subfolders),
 - baseSource: str -> common subpath for all the monitored folders,
 - sources: list -> list of groups that are monitored.

Each group is a dictionary:
 - name: str -> name of the group. Must be unique not to overwrite the data,
 - stations: list -> list of paths that will be monitored,
 - enable: bool -> disable/enable coping logs.

## How to run script
Script must be run with the command: 
```
python filetransfer.py "name"
```
where name is the name of the config file.

## Used modules

 - json
 - logging
 - sys
 - os
 - time
 - threading
 - shutil
 - watchdog
 - 
