# correct-onedrive-names

This script looks in a directory for subdirectories and files that have names that are not valid for OneDrive and replaces invalid characters with an underscore `_`. It will give a warning for filenames like `desktop.ini` but not rename them. It makes a CSV file that logs all changes and puts this in the same directory you supplied.

The script uses Python's `os` package to find and rename files, so it should work on any OS that can run Python.
