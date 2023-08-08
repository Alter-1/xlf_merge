# xlf_merge

automatically merges XLF translation files. There are two operation modes.

* merge all files specified with -i into single file specified with -b option. xlf_merge loads 1st file and attempts to merge rest ones into it.

* If first -i points to directory xlf_merge will enumerate .xlf files in it and try to merge it with file of the same name taken from 2nd -i parameter. Merged file will have the same name and will be placed in directory specified by -o 

If more than one record with the same ID is found, xlf_merge takes into account translation state (see Merge priority below) and use record with highest priority. If records have same priority, the 1st is used unless -f is specified.

## Usage:
```
  xlf_merge.py [<options>] -i <xlf1> -i <xlf2> [ -i <xlf3> ....] -o <xlf_merged>
  xlf_merge.py [<options>] -i <dir11> -i <dir2> -o <dir_merged>
```

Options:
```
  -v    verbose
  -f    force using last variant when merging records with same key/state
  -h    display help screen
```

## Merge priority
```
'translated':               5,
'needs-review-translation': 4,
'new':                      3,
'needs-translation':        2,
'needs-adaptation':         1
```

Origin:  https://alter.org.ua/soft/other/xlf_merge
