# OpenMW-ModChecker

Scans an `openmw.cfg` file to determine if a mod's files are overwritten by something later in the load order.

An individual mod can be scanned by providing its directory name as a command-line argument.

## Caveats

* For this script to work, you need to keep all your mods in one central directory.  See the included cfg file for an example of this (`TestMods` would be the central directory.)
* This central directory must be provided as a command-line argument, it cannot be inferred from the cfg file (yet, at least.)

## Usage

### Scan for a particular mod

    # Scans the given base mod directory for anything that override "CorrectUVTrees"
    ./openmw-modchecker.py --base-mod-dir ~/games/MorrowindMods --mod-dir-name CorrectUVTrees

### Scan all mods

    # Scan each directory in the given base mod directory, if it's a listed
    # data path then check every data path loaded after it to see if it is
    # overridden by anything after it.
    ./openmw-modchecker.py --base-mod-dir ~/games/MorrowindMods

### Log to a file

`openmw-modchecker` has no built-in logging, but you can use other shell commands to write output to a log:

    ./openmw-modchecker.py --base-mod-dir ~/games/MorrowindMods | tee -a /tmp/modchecker-$(date +%F)-$(date +%T).txt

## Test cases

Included are files for use as test cases:

    # This should be totally overridden
    ./openmw-modchecker.py -D ./TestMods -f ./openmw-test.cfg -m TestMod1

    # This should have one remaining file
    ./openmw-modchecker.py -D ./TestMods -f ./openmw-test.cfg -m TestMod2

    # This should have four remaining files
    ./openmw-modchecker.py -D ./TestMods -f ./openmw-test.cfg -m TestMod3

    # This should error out because there's no data paths
    ./openmw-modchecker.py -D ./TestMods -f ./empty.cfg
