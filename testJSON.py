import json

with open('filetransfer.conf', 'r') as f:
    config = json.load(f)
    print(config)