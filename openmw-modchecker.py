#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import sys
import pathlib

from collections import OrderedDict
from typing import Union as T


DEFAULT_CFG_FILE = os.path.join(os.getenv("HOME"), ".config", "openmw", "openmw.cfg")
DESC = "Scan mod directories to determine if an entire mod is being overwritten by something later in the load order.  Checks all found mods by default."
LICENSE = "GPLv3"
LOGFMT = "%(asctime)s : %(message)s"
PROG = "openmw-modchecker"
OK_DIRS = [
    "bookart",
    "fonts",
    "icons",
    "meshes",
    "music",
    "sound",
    "splash",
    "textures",
]
VERSION = "0.1"
VERY_LOUD = False


def emit_log(msg: str, level=logging.INFO, *args, **kwargs) -> None:
    """Logging wrapper."""

    if level == logging.DEBUG:
        logging.debug(msg, *args, **kwargs)
    elif level == logging.INFO:
        logging.info(msg, *args, **kwargs)
    elif level == logging.WARN:
        logging.warn(msg, *args, **kwargs)
    elif level == logging.ERROR:
        logging.error(msg, *args, **kwargs)


def error_and_die(msg: str) -> SystemExit:
    """Call sys.ext(1) with a formatted error message."""
    emit_log("ERROR: " + msg, level=logging.ERROR)
    sys.exit(1)


def check_openmw_cfg_path(path: str) -> T[bool, SystemExit]:
    """Check if the given openmw.cfg path exists, exit 1 if not."""
    path_exists = os.path.isfile(path)
    if not path_exists:
        error_and_die("{} could not be found!".format(path))
    return True


def get_mod_file_list(mod_dir: str) -> list:
    """
    Given a mod_dir, scan that directory and return a list
    of files found within any "ok dirs" that may exist.
    """
    _mod_files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(mod_dir):
        if f:
            for _file in f:
                full_file_path = os.path.join(r, _file)
                for d in OK_DIRS:
                    if d in full_file_path.lower():
                        _mod_files.append(_file.lower())
                        # TODO: maybe add a super verbose mode for this
                        # emit_log("Added file '{0}' for path '{1}'...".format(_file, mod_dir), level=logging.DEBUG)
    return _mod_files


def read_openmw_cfg(cfg_path: str) -> list:
    """
    Given a cfg_path, scan that file for anything that looks
    like an OpenMW data path and return any found in a list.
    """
    count = 1
    data_paths = OrderedDict()
    check_openmw_cfg_path(cfg_path)
    cfg = open(cfg_path)
    line_list = cfg.readlines()
    cfg.close()
    for line in line_list:
        if line.startswith("data=") and "data files" not in line.lower():
            data_paths.update({count: line})
            count += 1
    return data_paths


def mod_name_from_data_path(datastring: str) -> str:
    """Hacky, not-foolproof way to get a mod name from a file path."""
    return (
        datastring.split('data="')[-1].split(os.path.sep)[-1].replace('"', "").rstrip()
    )


def check_mod(_mod: str, all_paths: list, base_dir: str) -> bool:
    """
    The meat and potatoes, so to say.

    Given a mod name (_mod), list of paths (all_paths), and a base directory
    (base_dir) for all mods to be scanned against, compare found mods against
    the one given to determine if the entirety of the given mod's files are
    overridden by something later in the load order.
    """
    ow_by = []
    mod1_files = get_mod_file_list(os.path.join(base_dir, _mod))
    if len(mod1_files) == 0:
        emit_log("Mod {} has no files!".format(_mod), level=logging.DEBUG)
        return False

    start_checking = False
    for num, p in all_paths.items():
        if os.path.sep + _mod in p and not start_checking:
            emit_log(
                "Found mod '{0}' in the load order at position #{1}, start checking now".format(
                    _mod, num
                )
            )
            start_checking = True
        elif start_checking:
            emit_log("", level=logging.DEBUG)
            if len(mod1_files) > 0:
                emit_log(
                    "Load order #{0}, path: {1}".format(num, p.rstrip()),
                    level=logging.DEBUG,
                )
                emit_log(
                    "Mod '{0}' files left to check: {1}".format(_mod, len(mod1_files)),
                    level=logging.DEBUG,
                )
                next_mod = mod_name_from_data_path(p)
                if next_mod == _mod:
                    emit_log("next_mod == _mod, skipping it", level=logging.DEBUG)
                    continue
                emit_log(
                    "Checking '{0}' against '{1}'".format(_mod, next_mod),
                    level=logging.DEBUG,
                )
                next_mod_files = get_mod_file_list(os.path.join(base_dir, next_mod))
                if len(next_mod_files) == 0:
                    emit_log(
                        "Mod '{}' has no files to check".format(next_mod),
                        level=logging.DEBUG,
                    )
                    continue
                else:
                    emit_log(
                        "Mod '{0}' files to check: {1}".format(
                            next_mod, len(next_mod_files)
                        ),
                        level=logging.DEBUG,
                    )
                    for _file in next_mod_files:
                        if _file in mod1_files:
                            mod1_files.remove(_file)
                            emit_log(
                                "Mod '{0}' overwrites file '{1}' from the source mod '{2}'".format(
                                    next_mod, _file, _mod
                                ),
                                level=logging.DEBUG,
                            )
                            if next_mod not in ow_by:
                                ow_by.append(next_mod)
            else:
                emit_log(
                    "Mod '{0}' has been overwritten by the following mods:".format(_mod)
                )
                for m in ow_by:
                    emit_log("----> " + m)
                return False

            emit_log(
                "Mod '{0}' does not overwrite mod '{1}'!".format(next_mod, _mod),
                level=logging.DEBUG,
            )
    emit_log("", level=logging.DEBUG)
    emit_log(
        "Mod '{0}' can stay, remaining filecount: {1}".format(_mod, len(mod1_files))
    )
    # TODO: extra verbose
    if len(mod1_files) < 50 or VERY_LOUD:
        emit_log("Leftover files list:", level=logging.DEBUG)
        for f in mod1_files:
            emit_log("==> " + f, level=logging.DEBUG)
    else:
        emit_log("Too many leftover files to list!", level=logging.DEBUG)


def init_logging(log_lvl: str) -> bool:
    """Wrapper for initializing logging."""
    logging.basicConfig(format=LOGFMT, level=log_lvl, stream=sys.stdout)


def parse_argv() -> None:
    """Set up args and parse them."""
    parser = argparse.ArgumentParser(description=DESC, prog=PROG)
    req_args = parser.add_mutually_exclusive_group(required=True)
    req_args.add_argument(
        "-D",
        "--base-mod-dir",
        help="Path to the base mod directory containing all other mods.",
    )
    options = parser.add_argument_group("Options")
    options.add_argument(
        "-f",
        "--openmw-cfg-file",
        dest="openmw_cfg",
        metavar="CFG FILE",
        help="Specify the path to an openmw.cfg file.",
    )
    options.add_argument(
        "-m", "--mod-dir-name", help="Directory name of a single mod to be checked."
    )
    options.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print out (a lot) more information about what's going on.",
    )
    return parser.parse_args()


def main():
    base_mod_dir = None
    mod_dict = {}
    openmw_cfg = DEFAULT_CFG_FILE
    single_mod = None
    verbose = False

    parsed = parse_argv()

    if parsed.verbose:
        verbose = True
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init_logging(log_level)
    emit_log("VERBOSE ON!", level=logging.DEBUG)
    start = datetime.datetime.now()
    if (
        "-h" not in sys.argv
        and "--help" not in sys.argv
        and "--version" not in sys.argv
    ):
        emit_log("Begin scan - {0} (v{1})".format(PROG, VERSION))

    if parsed.base_mod_dir:
        base_mod_dir = parsed.base_mod_dir
        emit_log("BASE MOD DIR: " + base_mod_dir, level=logging.DEBUG)
    if parsed.mod_dir_name:
        single_mod = parsed.mod_dir_name
        emit_log("SINGLE MOD: " + single_mod, level=logging.DEBUG)
    if parsed.openmw_cfg:
        openmw_cfg = parsed.openmw_cfg
        emit_log("OPENMW.CFG: " + openmw_cfg, level=logging.DEBUG)

    all_data_paths = read_openmw_cfg(openmw_cfg)

    if len(all_data_paths.values()) == 0:
        error_and_die("There are no data paths in the given cfg file")

    if single_mod:
        emit_log("Checking single mod: '{}'".format(single_mod))
        num_paths_to_check = len(all_data_paths.values())
        if num_paths_to_check > 0:
            emit_log(
                "There are {} paths to check".format(str(num_paths_to_check)),
                level=logging.DEBUG,
            )
            _mod_files_list = get_mod_file_list(os.path.join(base_mod_dir, single_mod))
            mod_dict.update({single_mod: _mod_files_list})
            emit_log(
                "There are {0} files in the mod '{1}'".format(
                    str(len(_mod_files_list)), single_mod
                ),
                level=logging.DEBUG,
            )
            check_mod(single_mod, all_data_paths, base_mod_dir)
        else:
            # Either single_mod is not a real mod or it actually has no files.
            emit_log("No paths to check for {}!!!!".format(single_mod))
    else:
        for data_mod_path in all_data_paths.values():
            if data_mod_path.startswith("data="):
                mod_path = data_mod_path.replace("data=", "")
                mod_path = data_mod_path.strip("'\"\n")  # remove quotes and newline
                if mod_path == base_mod_dir:
                    continue
                _mod_files_list = get_mod_file_list(mod_path)
                single_mod = pathlib.Path(mod_path).name
                mod_dict.update({single_mod: _mod_files_list})
                emit_log(
                    "There are {0} files in the mod '{1}'".format(
                        str(len(_mod_files_list)), single_mod
                    ),
                    level=logging.DEBUG,
                )
                check_mod(single_mod, all_data_paths, base_mod_dir)
    emit_log("End scan - {0} (v{1})".format(PROG, VERSION))
    end = datetime.datetime.now()
    duration = end - start
    minutes = int(duration.total_seconds() // 60)
    seconds = int(duration.total_seconds() % 60)
    emit_log(
        "Took {m} minutes, {s} seconds.".format(m=minutes, s=seconds),
        level=logging.DEBUG,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("  CTRL-C DETECTED! EXITING...")
        sys.exit(2)
