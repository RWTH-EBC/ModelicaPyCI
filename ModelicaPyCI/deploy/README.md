# What is it?
Automatic merge of the IBPSA library into AixLib. Compare the latest conversion script of AixLib with the 
latest conversion script of IBPSA.
## ibpsa_merge.py
#### Parser Arguments
| Parser Arguments  | Description      | 
|-------------------| ------------------------- | 
|--library-dir|path to the library scripts  | 
|--merge-library-dir| path to the merge library scripts | 
|--mos-path| Folder where the conversion scripts are stored temporarily | 
|--library|  Library to be merged into| 
|--merge-library|Library to be merged | 

#### Example: Execution on gitlab runner (linux)
    python modelicapyci_tests/CITests/deploy/IBPSA_Merge/ibpsa_merge.py 
