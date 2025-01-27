#!/usr/bin/env python3
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###
# Reset the Date Modified and Date Created for downloaded files.
#
# This is useful for sorting "newly added" media.
# This should run before other scripts.
#
# NOTE: This script requires Python to be installed on your system.
### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################
import os
import sys

# NZBGet Exit Codes
NZBGET_POSTPROCESS_PARCHECK = 92
NZBGET_POSTPROCESS_SUCCESS = 93
NZBGET_POSTPROCESS_ERROR = 94
NZBGET_POSTPROCESS_NONE = 95

if 'NZBOP_SCRIPTDIR' not in os.environ:
    print('This script can only be called from NZBGet (11.0 or later).')
    sys.exit(0)

if os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print(f'NZBGet Version {os.environ["NZBOP_VERSION"]} is not supported. Please update NZBGet.')
    sys.exit(0)

print(f'Script triggered from NZBGet Version {os.environ["NZBOP_VERSION"]}')
status = 0
if 'NZBPP_TOTALSTATUS' in os.environ:
    if not os.environ['NZBPP_TOTALSTATUS'] == 'SUCCESS':
        print(f'Download failed with status {os.environ["NZBPP_STATUS"]}')
        status = 1

else:
    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        print('Par-repair failed, setting status "failed".')
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print('Unpack failed, setting status "failed".')
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            print('Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status "failed".')
            print('Please check your Par-check/repair settings for future downloads.')
            status = 1

        else:
            print('Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful.')
            print('Please check your Par-check/repair settings for future downloads.')

# Check if destination directory exists (important for reprocessing of history items)
if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
    print(f'Nothing to post-process: destination directory {os.environ["NZBPP_DIRECTORY"]} doesn\'t exist. Setting status "failed".')
    status = 1

# All checks done, now launching the script.
if status == 1:
    sys.exit(NZBGET_POSTPROCESS_NONE)

directory = os.path.normpath(os.environ['NZBPP_DIRECTORY'])
for dirpath, dirnames, filenames in os.walk(directory):
    for file in filenames:
        filepath = os.path.join(dirpath, file)
        print(f'reseting datetime for file {filepath}')
        try:
            os.utime(filepath, None)
            continue
        except:
            print(f'Error: unable to reset time for file {file}')
            sys.exit(NZBGET_POSTPROCESS_ERROR)
sys.exit(NZBGET_POSTPROCESS_SUCCESS)
