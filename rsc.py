#!/usr/bin/python3

import argparse
import logging
import os
import glob
import struct

def main():
    if not os.path.isdir(args.input):
        raise TypeError("Input argument must be a directory.")

    if os.path.isdir(args.export):
        args.export = os.path.join(args.export, os.path.split(args.input)[1])

    files = [f for f in os.listdir(args.input) if os.path.isfile(os.path.join(args.input, f))]
    with open(args.export, 'wb') as out:
        out.write(b'BWRF10')
        out.write(struct.pack("<L", len(files)))

        pos = out.tell() + ((0x0c + 0x04 + 0x04) * len(files))
        for name in files:
            if len(name) > 0x0c:
                raise TypeError("Long file names not permitted in RSC archives")

            out.write(str.encode(name) + (b'\x00'*(0x0c - len(name))))
            out.write(struct.pack("<L", pos))

            size = os.path.getsize(os.path.join(args.input, name))
            out.write(struct.pack("<L", size))
            pos += size
        
        for name in files:
            with open(os.path.join(args.input, name), 'rb') as inf:
                out.write(inf.read())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="rsc", formatter_class=argparse.RawTextHelpFormatter,
         description="""Create JumpStart RSC archives."""
    )

    parser.add_argument(
        "input", help="Pass a directory to create an RSC archive with the files in the directory."
    )

    parser.add_argument(
        "export", nargs='?', default=".",
        help="""Specify the location for exporting assets, or omit to skip export. If a
filename is not specified, the archive will be created with the name of the
input directory."""
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    main()
