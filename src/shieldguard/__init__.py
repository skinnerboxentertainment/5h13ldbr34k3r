"""Package entry point: `shieldguard <url-or-html>` CLI."""

import argparse
import sys

from .core import main as core_main


def main(argv=None):
    core_main(argv)


if __name__ == "__main__":
    main()
