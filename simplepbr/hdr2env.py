#!/usr/bin/env python
import argparse
import time


import panda3d.core as p3d

import simplepbr

def main():
    parser = argparse.ArgumentParser(
        description='CLI tool to convert HDR cubemap files to simplepbr env files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('src', type=str, help='source file')
    parser.add_argument('dst', type=str, help='destination file')

    args = parser.parse_args()

    envmap = simplepbr.EnvMap.from_file_path(args.src)
    while not envmap.is_prepared.done():
        p3d.AsyncTaskManager.get_global_ptr().poll()
        time.sleep(1)

    envmap.write(args.dst)

if __name__ == '__main__':
    main()
