#!/usr/bin/env python3
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###
# Extract archives using password list.
#
# This script will attempt to use all passwords from a supplied list to extract a password.
#
# NOTE: This script requires Python to be installed on your system.
##############################################################################
### OPTIONS                                                                ###
# Password File.
#
# Enter the Path to a plain-text file with a single password on each line.
# Each Password will be used to attempt extraction.
# PasswordFile="/share/Download/password.txt"
# Windows
# SevenZip command.
#
# Set the 7zip.exe path for Windows Systems.
# SevenZip=
# Posix
# Niceness for external extraction process.
#
# Set the Niceness value for the nice command (Linux). These range from -20 (most favorable to the process) to 19 (least favorable to the process).
# niceness=10
# ionice scheduling class (0, 1, 2, 3).
#
# Set the ionice scheduling class (Linux). 0 for none, 1 for real time, 2 for best-effort, 3 for idle.
# ionice_class=2
# ionice scheduling class data.
#
# Set the ionice scheduling class data (Linux). This defines the class data, if the class accepts an argument. For real time and best-effort, 0-7 is valid data.
# ionice_classdata=4
### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################
import os
import platform
import re
import sys
from subprocess import call
from subprocess import Popen
from time import sleep

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
        status = 0

else:
    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        print('Par-repair failed, setting status "failed".')
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

PASSWORDSFILE = os.environ['NZBPO_PASSWORDFILE']
SEVENZIP = os.environ['NZBPO_SEVENZIP']
ARCHIVE = [
    re.compile(r'.r\d{2}$', re.I),
    re.compile(r'.part\d+.rar$', re.I),
    re.compile('.rar$', re.I), '.rar',
]

# Using Windows
if platform.system() == 'Windows':
    if not os.path.exists(SEVENZIP):
        print(' Could not find 7-zip, Exiting')
        sys.exit(NZBGET_POSTPROCESS_ERROR)
    else:
        cmd_7zip = [SEVENZIP, 'x', '-y']
        ext_7zip = [
            '.rar', '.zip', '.tar.gz', 'tgz', '.tar.bz2',
            '.tbz', '.tar.lzma', '.tlz', '.7z', '.xz',
        ]
        EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
# Using unix
else:
    required_cmds = [
        'unrar', 'unzip', 'tar',
        'unxz', 'unlzma', '7zr', 'bunzip2',
    ]
    EXTRACT_COMMANDS = {
        '.rar': ['unrar', 'x', '-o+', '-y'],
        '.tar': ['tar', '-xf'],
        '.zip': ['unzip'],
        '.tar.gz': ['tar', '-xzf'], '.tgz': ['tar', '-xzf'],
        '.tar.bz2': ['tar', '-xjf'], '.tbz': ['tar', '-xjf'],
        '.tar.lzma': ['tar', '--lzma', '-xf'], '.tlz': ['tar', '--lzma', '-xf'],
        '.tar.xz': ['tar', '--xz', '-xf'], '.txz': ['tar', '--xz', '-xf'],
        '.7z': ['7zr', 'x'],
    }    # Test command exists and if not, remove
    devnull = open(os.devnull, 'w')
    for cmd in required_cmds:
        # note, returns 0 if exists, or 1 if doesn't exist.
        if call(['which', cmd], stdout=devnull, stderr=devnull):
            # we do have "7z" command
            if cmd == '7zr' and not call(['which', '7z']):
                EXTRACT_COMMANDS['.7z'] = ['7z', 'x']
            # we do have "7za" command
            elif cmd == '7zr' and not call(['which', '7za']):
                EXTRACT_COMMANDS['.7z'] = ['7za', 'x']
            else:
                for k, v in list(EXTRACT_COMMANDS.items()):
                    if cmd in v[0]:
                        print(f'{cmd} not found, disabling support for {k}')
                        del EXTRACT_COMMANDS[k]
    devnull.close()

    if not EXTRACT_COMMANDS:
        print('No archive extracting programs found, plugin will be disabled')
        sys.exit(NZBGET_POSTPROCESS_ERROR)

    devnull = open(os.devnull, 'w')
    NICENESS = []
    try:
        subprocess.Popen(['nice'], stdout=devnull, stderr=devnull).communicate()
        NICENESS.extend(['nice', f'-n{os.environ["NZBPO_NICENESS"]}'])
    except:
        pass
    try:
        subprocess.Popen(['ionice'], stdout=devnull, stderr=devnull).communicate()
        try:
            NICENESS.extend(['ionice', f'-c{os.environ["NZBPO_IONICE_CLASS"]}'])
        except:
            pass
        try:
            if 'ionice' in NICENESS:
                NICENESS.extend([f'-n{os.environ["NZBPO_IONICE_CLASSDATA"]}'])
            else:
                NICENESS.extend(['ionice', f'-n{os.environ["NZBPO_IONICE_CLASSDATA"]}'])
        except:
            pass
    except:
        pass
    devnull.close()


def extract(directory, filePath):
    success = 0
    ext = os.path.splitext(filePath)
    cmd = []
    part = 1

    if ext[1] in ('.gz', '.bz2', '.lzma'):
        # Check if this is a tar
        if os.path.splitext(ext[0])[1] == '.tar':
            cmd = EXTRACT_COMMANDS['.tar' + ext[1]]
    # don't extract these comic book archives.
    elif ext[1] in ('.cb7', '.cba', '.cbr', '.cbt', '.cbz'):
        print("don't extract these comic book archives")
        return True
    elif ext[1] in EXTRACT_COMMANDS:
        if re.match(r'.part\d+', os.path.splitext(ext[0])[1]):
            part = int(
                re.match(
                    r'.part(\d+)',
                    os.path.splitext(ext[0])[1],
                ).groups()[0],
            )
        if re.match(r'.\d+', os.path.splitext(ext[0])[1]):
            part = int(
                re.match(r'.(\d+)', os.path.splitext(ext[0])[1]).groups()[0],
            )
        if part == 1:
            cmd = EXTRACT_COMMANDS[ext[1]]
        else:
            print(f'ignoring part {part}')
            return True
    elif os.path.splitext(ext[0])[1] in EXTRACT_COMMANDS:
        if re.match(r'.part\d+', ext[1]):
            part = int(re.match(r'.part(\d+)', ext[1]).groups()[0])
        if re.match(r'.\d+', ext[1]):
            part = int(re.match(r'.(\d+)', ext[1]).groups()[0])
        if part == 1:
            cmd = EXTRACT_COMMANDS[os.path.splitext(ext[0])[1]]
        else:
            print(f'ignoring part {part}')
            return True
    else:
        print(f'Not a known archive file type: {ext[1]}')
        return True

    print(f'Extracting {filePath}')
    if PASSWORDSFILE != '' and os.path.isfile(PASSWORDSFILE):
        passwords = [
            line.strip()
            for line in open(os.path.normpath(PASSWORDSFILE))
        ]
        print(f'Found {len(passwords)} passwords to try')
    else:
        passwords = []
        print(f'Could not find password file {PASSWORDSFILE}')

    pwd = os.getcwd()  # Get our Present Working Directory
    # Not all unpack commands accept full paths, so just extract into this directory
    os.chdir(directory)
    devnull = open(os.devnull, 'w')

    try:  # now works same for nt and *nix
        cmd.append(filePath)  # add filePath to final cmd arg.

        if platform.system() != 'Windows':
            cmd = NICENESS + cmd
        cmd2 = cmd
        cmd2.append('-p-')  # don't prompt for password.
        # should extract files fine.
        p = Popen(cmd2, stdout=devnull, stderr=devnull)
        res = p.wait()

        if res == 0:
            print(f'Extraction was successful for {filePath}')
            success = 1
        elif len(passwords) > 0:
            for password in passwords:
                print(f'Attempting to extract with password [{password}]')
                # if edited in windows or otherwise if blank lines.
                if password == '':
                    continue
                cmd2 = cmd
                # append password here.
                passcmd = f'-p{password}'
                cmd2.append(passcmd)
                # print cmd2
                # should extract files fine.
                p = Popen(cmd2, stdout=devnull, stderr=devnull)
                res = p.wait()
                if res == 0:
                    print(f'Extraction was successful for {filePath} using password: {password}')
                    success = 1
                    break
                else:
                    print(f'Extraction failed for {filePath} using password: {password}')
                    continue
    except:
        print(f'Extraction failed for {filePath}. Could not call command {cmd}')
        devnull.close()
        os.chdir(pwd)
        return False

    devnull.close()
    os.chdir(pwd)  # Go back to our Original Working Directory
    if success:
        # sleep to let files finish writing to disk
        sleep(3)
        return True
    else:
        print(f'Extraction failed for {filePath}. Result was {res}')
        return False


failed = 0
for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
    for file in filenames:
        filePath = os.path.join(dirpath, file)
        fileName, fileExtension = os.path.splitext(file)
        # if fileExtension in ARCHIVE:  # If the file is an archive
        if extract(os.environ['NZBPP_DIRECTORY'], filePath):
            failed += 0
        else:
            failed += 1

if failed:
    sys.exit(NZBGET_POSTPROCESS_ERROR)
else:
    os.environ['NZBPP_TOTALSTATUS'] = 'SUCCESS'
    sys.exit(NZBGET_POSTPROCESS_SUCCESS)
