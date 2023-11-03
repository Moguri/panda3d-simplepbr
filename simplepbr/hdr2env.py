#!/usr/bin/env python
import argparse


import panda3d.core as p3d

import simplepbr
from simplepbr.envmap import (
    DEFAULT_PREFILTERED_SIZE,
    DEFAULT_PREFILTERED_SAMPLES,
)

def main() -> None:
    parser = argparse.ArgumentParser(
        description='CLI tool to convert HDR cubemap files to simplepbr env files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('src', type=str, help='source file')
    parser.add_argument('dst', type=str, help='destination file')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true'
    )
    parser.add_argument(
        '--prefiltered-size',
        type=int,
        help='the size to use for both dimensions of the prefiltered cubemap',
        default=DEFAULT_PREFILTERED_SIZE
    )
    parser.add_argument(
        '--prefiltered-samples',
        type=int,
        help='the number of samples to use for each pixel of the prefiltered cubemap',
        default=DEFAULT_PREFILTERED_SAMPLES
    )

    args = parser.parse_args()

    if args.verbose:
        p3d.load_prc_file_data('', 'notify-level-simplepbr debug')

    envmap = simplepbr.EnvMap.from_file_path(
        args.src,
        prefiltered_size=args.prefiltered_size,
        prefiltered_samples=args.prefiltered_samples,
        blocking_prepare=True,
    )

    envmap.write(args.dst)

if __name__ == '__main__':
    main()
