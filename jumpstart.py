#!/usr/bin/python3

import argparse
import logging
import struct
import os
from pathlib import Path
import glob
import mmap
import io

from mrcrowbar import utils

def value_assert(stream, target, type="value", warn=False):
    ax = stream
    try:
        ax = stream.read(len(target))
    except AttributeError:
        pass

    msg = "Expected {} {}{}, received {}{}".format(
        type, target, " (0x{:0>4x})".format(target) if isinstance(target, int) else "",
        ax, " (0x{:0>4x})".format(ax) if isinstance(ax, int) else "",
    )
    if warn and ax != target:
        logging.warning(msg)
    else:
        assert ax == target, msg

class Object:
    def __format__(self, spec):
        return self.__repr__()

class Rsc(Object):
    def __init__(self, stream, name=None):
        logging.info("*** Scanning RSC file... ***")
        stream.seek(0)
        value_assert(stream.read(4), b'BWRF', "magic number")
        self.version = stream.read(2)

        file_count = struct.unpack("<L", stream.read(4))[0]
        logging.info(" ({} files in archive)".format(file_count))
        self.files = []
        for _ in range(file_count):
            record = {
                "name": stream.read(0x0c).replace(b'\x00', b'').decode("utf-8"),
                "start": struct.unpack("<L", stream.read(4))[0],
                "size": struct.unpack("<L", stream.read(4))[0],
            }

            self.files.append(record)
            logging.debug(record)

        if args.export:
            directory = os.path.join(args.export, name)
            Path(directory).mkdir(parents=True, exist_ok=True)
        else:
            directory = None

        for entry in self.files:
            assert stream.tell() == entry["start"]
            data = stream.read(entry["size"])
            if directory:
                with open(os.path.join(directory, entry["name"]), 'wb') as output:
                    output.write(data)

        logging.info("*** End RSC file... ***")
def process(filename):
    logging.debug("Processing file: {}".format(filename))
    with open(filename, mode='rb') as f:
        stream = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
        t = filename[-3:].lower()
        try:
            if t  == "rsc":
                # Top-level archive
                Rsc(stream, name=os.path.split(filename)[-1])
            elif t == "atr":
                # Actor
                Atr(stream)
            else:
                raise TypeError("Unknown file type provided: {}".format(t))
        except Exception as e:
            logging.error("Exception at {}:{:012x}".format(filename, stream.tell()))
            raise

def main():
    if os.path.isdir(args.input):
        for name in glob.glob(os.path.join(args.input, "*.RSC")):
            process(name)
    else:
        process(args.input)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="jumpstart", formatter_class=argparse.RawTextHelpFormatter,
         description="""Parse asset structures and extract assets from JumpStart interactive titles."""
    )

    parser.add_argument(
        "input", help="Pass a RSRC (resource) filename to process the file,\n or pass a game data directory to process the whole game."
    )

    parser.add_argument(
        "export", nargs='?', default=None,
        help="Specify the location for exporting assets, or omit to skip export."
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    main()
