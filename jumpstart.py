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


class Xdt(Object): # SDT (SND) or TDT (TLK)
    def __init__(self, stream, snd):
        # TODO: Determine how many embedded WAVs there are in advance.
        snd.seek(0)
        length = os.fstat(snd.fileno()).st_size

        self.records = []
        record = XdtRecord(stream, snd)
        while record.end < length:
            self.records.append(record)
            record = XdtRecord(stream, snd)

        self.records.append(record)

class XdtRecord(Object):
    def __init__(self, stream, snd):
        # 0x2e: In the master SND/TLK, there are 0x2e bytes of header
        # information before the audio data begins.
        self.name = stream.read(0x0c).replace(b'\x00', b'').decode("utf-8")
        self.start = struct.unpack("<L", stream.read(4))[0] + 0x2e
        self.end = struct.unpack("<L", stream.read(4))[0] + 0x2e

        snd.seek(self.start)
        self.data = snd.read(self.end - self.start)

class Atr(Object):
    def __init__(self, stream):
        value_assert(stream.read(3), b'ATR', "magic number")
        self.name = stream.read(0x10).replace(b'\x00', b'').decode("utf-8")
        self.background = stream.read(0x10).replace(b'\x00', b'').decode("utf-8")
        self.name2 = stream.read(0x10).replace(b'\x00', b'').decode("utf-8")
        logging.debug("Atr: Name: {} \\ Background: {}".format(self.name, self.background))
        unk1 = struct.unpack("<L", stream.read(4))[0]
        logging.debug("Atr: Unk1: {}".format(unk1))
        value_assert(stream.read(4), b'\x00'*4)

        self.width = struct.unpack("<L", stream.read(4))[0]
        self.height = struct.unpack("<L", stream.read(4))[0]
        frame_count = struct.unpack("<L", stream.read(4))[0]
        logging.debug("Atr: Expecting {} frames ({} x {})".format(frame_count, self.width, self.height))

        self.frames = []
        for i in range(frame_count):
            logging.debug("Atr: Reading frame {}:".format(i))
            entity = AtrFrame(stream)
            self.frames.append(entity)
            logging.debug(entity.__dict__)
            logging.debug("Frame Dimensions: {} x {}".format(entity.right-entity.left, entity.bottom-entity.top))

            print()

class AtrFrame(Object):
    def __init__(self, stream):
        self.left = struct.unpack("<L", stream.read(4))[0]
        self.top = struct.unpack("<L", stream.read(4))[0]
        self.right = struct.unpack("<L", stream.read(4))[0]
        self.bottom = struct.unpack("<L", stream.read(4))[0]

        unk1 = struct.unpack("<L", stream.read(4))[0]
        logging.debug("AtrFrame: Unk1: {}".format(unk1))

        unk2 = stream.read(8)
        logging.debug("AtrFrame: Unk2: {}".format(unk2))

        self.length = struct.unpack("<L", stream.read(4))[0]
        logging.debug("(@0x{:012x}) AtrFrame: Reading 0x{:04x} bytes".format(stream.tell(), self.length))
        utils.hexdump(stream.read(self.length))

    @property
    def width(self):
        return self.right-self.left

    @property
    def height(self):
        return self.bottom-self.top

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
