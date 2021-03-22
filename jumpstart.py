#!/usr/bin/python3

import argparse
import logging
import struct

import mmap

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
    def __init__(self, stream):
        stream.seek(0)
        value_assert(stream.read(4), b'BWRF', "magic number")

        self.version = stream.read(2)
        file_count = struct.unpack("<L", stream.read(4))[0]

        self.files = []
        for _ in range(file_count):
            record = {
                "name": stream.read(0x0c).replace(b'\x00', b'').decode("utf-8"),
                "start": hex(struct.unpack("<L", stream.read(4))[0]),
                "size": hex(struct.unpack("<L", stream.read(4))[0]),
            }

            self.files.append(record)
            print(record)

def main():
    with open(args.input, mode='rb') as f:
        stream = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
        Rsc(stream)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="jumpstart", formatter_class=argparse.RawTextHelpFormatter,
         description="""Parse asset structures and extract assets from JumpStart interactive titles."""
    )

    parser.add_argument(
        "input", help="Pass a RSRC (resource) filename to process the file,\n or pass a game data directory to process the whole game."
    )

    args = parser.parse_args()
    main()
