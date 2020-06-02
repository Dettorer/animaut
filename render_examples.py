#!/usr/bin/env python
import manimlib.config
import manimlib.constants
import manimlib.extract_scene
import sys


if __name__ == "__main__":
    sys.argv.insert(1, "examples/examples.py")
    args = manimlib.config.parse_cli()
    config = manimlib.config.get_configuration(args)
    manimlib.constants.initialize_directories(config)
    manimlib.extract_scene.main(config)
