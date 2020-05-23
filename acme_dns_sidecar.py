from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from tomlkit.toml_file import TOMLFile


def entrypoint():
    args = get_program_args()
    toml = TOMLFile(args.config).read()
    print(toml)
    return 0


def get_program_args():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c',
        dest='config',
        default='/etc/acme-dns/config.cfg',
        metavar='config_file',
        help='path to configuration file, can use the same file as acme-dns',
    )
    return parser.parse_args()


if __name__ == "__main__":
    import sys
    ret = entrypoint()
    sys.exit(ret)
