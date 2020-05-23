from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from tomlkit.toml_file import TOMLFile


class ConfigurationError(Exception):
    pass


class InvalidConfiguration(ConfigurationError):
    pass


def entrypoint():
    args = get_program_args()
    config = read_config(args.config)
    print(config)
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


def read_config(path):
    toml = TOMLFile(path).read()
    config = {
        'database': {
            'engine': 'sqlite3',
            'connection': '/var/lib/acme-dns/acme-dns.db',
        },
        'sidecar': {
            'secrets': {
                'field_selector': None,
                'label_selector': None,
            },
        },
    }
    config = validate_config(config, toml)
    if config['database']['engine'] != 'sqlite3':
        raise InvalidConfiguration('only sqlite3 database engine is supported')
    return config


def validate_config(config, toml, parent_prefix=None):
    if parent_prefix is None:
        parent_prefix = []
    for key in config:
        if key in toml:
            prefix = parent_prefix + [key]
            path = '.'.join(prefix)
            if isinstance(config[key], dict):
                if not isinstance(toml[key], dict):
                    raise ConfigurationError('%s is not a table' % path)
                config[key] = validate_config(config[key], toml[key], prefix)
            else:
                if not isinstance(toml[key], str):
                    raise ConfigurationError('%s is not a string' % path)
                config[key] = toml[key]
    return config


if __name__ == "__main__":
    import sys
    ret = entrypoint()
    sys.exit(ret)
