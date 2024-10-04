import os           # for file operations
import warnings     # to warn about un-renamed files (rare)
import csv          # to log changes
import datetime     # to name the log file
import re           # to make duplicate file name resolution easier
import sys			# for command line arguments

if '-verbose' in sys.argv:
	verbosity = True
else:
	verbosity = False

while_limit = sys.getrecursionlimit()  # there is a while loop later. this caps it at a certain number

# get path to onedrive
path_to_onedrive = input('What folder should I check? ')

# function to correct file or folder names
def generate_valid_name(original_path:str, rename_tilde_dollarsign=False):
    '''original_path: the full path to the folder or file name you want to clean
    rename_tilde_dollarsign: True if you want to replace '~$' with '_'. These are typically temporary MS Office files
    returns the same path with a new name following these rules:
        removes leading and trailing spaces
        replaces any characters that OneDrive doesn't accept with an underscore
    '''
    # see https://support.microsoft.com/en-us/office/restrictions-and-limitations-in-onedrive-and-sharepoint-64883a5d-228e-48f5-b3d2-eb39e07630fa#invalidcharacters
    forbidden_substrings = ('"', '*', ':', '<', '>', '?', '/', '\\', '|', '_vti_',)
    # see https://support.microsoft.com/en-us/office/restrictions-and-limitations-in-onedrive-and-sharepoint-64883a5d-228e-48f5-b3d2-eb39e07630fa#invalidfilefoldernames
    forbidden_names = ('.lock', 'CON', 'PRN', 'AUX', 'NUL',
                       'COM0', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                       'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
                       'desktop.ini')
    # get the specific folder/file we want to rename
    original_basename = os.path.basename(original_path)
    # and its folder
    original_directory = os.path.dirname(original_path)
    # check for forbidden names
    if original_basename in forbidden_names:
        warnings.warn('Filename ' + original_path + ' has an explicitly prohibited name. It was not renamed.')
        return original_path
    # leave ~$ files alone
    elif '~$' in original_basename and not rename_tilde_dollarsign:
        warnings.warn('Filename ' + original_path + ' is probably a temporary MS Office file. It was not renamed.')
        return original_path
    else:
        # if not explicitly forbidden, do some replacements
        # start by removing leading spaces
        new_basename = original_basename.lstrip()
        # and trailing ones (including spaces between the file name and file extension)
        new_basename = os.path.splitext(new_basename)[0].rstrip() + os.path.splitext(new_basename)[1].rstrip()
        # remove initial '~$' if requested
        if rename_tilde_dollarsign:
            if new_basename[:2] == '~$':
                new_basename = new_basename[2:]
        # replace forbidden characters with underscores
        for substring in forbidden_substrings:
            new_basename = new_basename.replace(substring, '_')
        # join the new base name to the original dir
        new_path = os.path.join(original_directory, new_basename)
        return new_path

# to be able to recognize numbers more easily
digits = '1234567890'
# function to rename things and try to automatically add numbers to files that would
# otherwise have duplicate names
def rename_fixing_dupes(orig_name, new_name, verbose=False):
    '''renames a file, adding (or incrementing) a number to the end of the name if it would cause a duplicate name
        orig_name: path to the file
        new_name: new name for the file (including path)'''
    try:
        os.rename(orig_name, new_name)
    except FileExistsError:
        # if this would cause a redundant name, add a number to it
        # remove the file extension
        file_ext = os.path.splitext(new_name)[1]
        new_name = os.path.splitext(new_name)[0]
        if new_name[-1:] in digits:
            orig_number = re.search(r'\d*$', new_name).group()
            new_number = str(int(orig_number) + 1)
            new_name = new_name[:-len(orig_number)] + new_number
        else:
            new_name = new_name + ' 1'
        # reattach file extension
        new_name = new_name + file_ext
        os.rename(orig_name, new_name)
    if verbose:
        print(orig_name + ' renamed to ' + new_name)
    return new_name

# process datetime for the log filename
current_datetime = str(datetime.datetime.now())
# since this will be part of the filename, make it OneDrive-compliant
current_datetime = generate_valid_name(current_datetime)
# create the log filename
log_filename = os.path.join(path_to_onedrive, 'file_rename_' + current_datetime + '.csv')

# function to write the log file
def write_to_log(old_path, new_path, override_datetime=False, log_path = log_filename, audit=False):
    '''old_path: the original path
    new_path: what the original path was renamed to
    log_path: path to the log file that should be written to
    override_datetime: whether to replace the auto-generated datetime with your own string. Supply the string you want instead
    audit: if True, will return the row it would have written and not write anything'''
    with open(log_path, 'a', newline='') as logfile:
        logwriter = csv.writer(logfile)
        if override_datetime:
            row_to_write = [old_path, new_path, override_datetime]
        else:
            row_to_write = [old_path, new_path, str(datetime.datetime.now())]
        if audit:
            return row_to_write
        else:
            logwriter.writerow(row_to_write)
        
# write headers to log
write_to_log('old_path', 'new_path', override_datetime='datetime')

# find folders in root
if os.name == 'posix':
    # for Mac, exclude hidden folders in root only; otherwise timeout errors can happen (and these files probably shouldn't be changed anyway)
    unscanned_directories = [f.path for f in os.scandir(path_to_onedrive) if f.is_dir() and f.name[0] != '.']
else:
    unscanned_directories = [f.path for f in os.scandir(path_to_onedrive) if f.is_dir()]
# rename them - this happens level by level for cases like 'upperfolder:/lowerfolder:'
while_counter = 0
while unscanned_directories and while_counter < while_limit:
    while_counter += 1
    for i in range(len(unscanned_directories)):
        folder = unscanned_directories[i]
        # get the new name
        newname = generate_valid_name(folder)
        if newname != folder:
            # do the rename
            rename_fixing_dupes(folder, newname, verbose=verbosity)
            # record the name change
            write_to_log(folder, newname)
            # change it in the list
            unscanned_directories[i] = newname
    renamed_directories = unscanned_directories
    unscanned_directories = []
    # scan the next level
    for folder in renamed_directories:
        unscanned_directories.extend([f.path for f in os.scandir(folder) if f.is_dir()])
if while_counter == while_limit:
    warnings.warn('While loop reached limit of ' + str(while_limit) + ' loops. Some deep subdirectories may still have bad names.')

# get filenames
print('Finding files')
# for Macs, exclude hidden folders/files in root directory
if os.name == 'posix':
    # get folders directly in root of OneDrive that are not hidden
    subfolders = [f.path for f in os.scandir(path_to_onedrive) if f.is_dir() and f.name[0] != '.']
    # get files in root of OneDrive that are not hidden or special
    onedrive_files = [f.path for f in os.scandir(path_to_onedrive) if f.is_file() and f.name[0] != '.' and f.name != 'Icon']
    # add files from non-hidden subfolders
    for folder in subfolders:
        onedrive_files.extend([os.path.join(dir, file) for dir, subdirs, files in os.walk(folder) for file in files])
else:
    onedrive_files = [os.path.join(dir, file) for dir, subdirs, files in os.walk(path_to_onedrive) for file in files]
print('Renaming files')
for orig_file in onedrive_files:
    # get the new name
    newname = generate_valid_name(orig_file)
    if newname != orig_file:
        # rename
        rename_fixing_dupes(orig_file, newname, verbose=verbosity)
        # log
        write_to_log(orig_file, newname)
