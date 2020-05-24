from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from uuid import UUID
from base64 import b64decode
import re
import sqlite3
from contextlib import contextmanager
from os import lstat
from time import sleep
from tomlkit.toml_file import TOMLFile
import kubernetes
import bcrypt


class ConfigurationError(Exception):
    pass


class InvalidConfiguration(ConfigurationError):
    pass


def entrypoint():
    args = get_program_args()
    config = read_config(args.config)
    check_database(config)
    for secret in watch_secrets(config):
        register_secret(config, secret)
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


def get_current_namespace():
    path = '/var/run/secrets/kubernetes.io/serviceaccount/namespace'
    with open(path) as fobj:
        return fobj.read()


def watch_secrets(config):
    namespace = get_current_namespace()
    kubernetes.config.load_incluster_config()
    v1 = kubernetes.client.CoreV1Api()
    w = kubernetes.watch.Watch()
    args = {
        'namespace': namespace,
        'watch': True,
    }
    if config['sidecar']['secrets']['field_selector'] is not None:
        args['field_selector'] = config['sidecar']['secrets']['field_selector']
    if config['sidecar']['secrets']['label_selector'] is not None:
        args['label_selector'] = config['sidecar']['secrets']['label_selector']
    for event in w.stream(v1.list_namespaced_secret, **args):
        if event['type'] == 'ADDED' or event['type'] == 'MODIFIED':
            secret = event['object']
            data = decode_secret(secret.data)
            if not valid_secret(data):
                print('Ignoring invalid secret %s' % secret.metadata.name)
            else:
                yield data


def decode_secret(data):
    return {key: b64decode(value).decode() for key, value in data.items()}


def valid_secret(data):
    if not ('username' in data and 'password' in data and 'subdomain' in data):
        print('Missing field in secret')
        return False
    try:
        UUID(data['username'])
    except ValueError:
        print('username is not a valid UUID')
        return False
    pattern = re.compile('^[-_A-Za-z0-9]{40}$')
    if not pattern.match(data['password']):
        print('password is not valid')
        return False
    pattern = re.compile('^[a-z0-9]([-a-z0-9]*[a-z0-9])?$')
    if not pattern.match(data['subdomain']):
        print('subdomain is not valid')
        return False
    return True


@contextmanager
def get_database(config):
    exists = False
    while not exists:
        try:
            lstat(config['database']['connection'])
            exists = True
        except FileNotFoundError:
            print('sqlite3 database not found, waiting for it to be created')
            sleep(1)
    conn = sqlite3.connect(config['database']['connection'],
                           check_same_thread=False,
                           timeout=10.0)
    try:
        yield conn
    finally:
        conn.close()


def check_database(config):
    check_table_exists(config, 'records')
    check_table_exists(config, 'txt')


def check_table_exists(config, table):
    while True:
        with get_database(config) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' "
                      'AND name=?', (table,))
            if c.fetchone():
                return
        print('%s table not yet created, waiting for it to be created' % table)
        sleep(1)


def password_hash(password):
    return bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())


def register_secret(config, secret):
    print('Register username %s' % secret['username'])
    password = password_hash(secret['password'])
    with get_database(config) as conn:
        try:
            c = conn.cursor()
            c.execute('INSERT INTO records '
                      '(Username, Password, Subdomain, AllowFrom) '
                      "VALUES(?, ?, ?, '[]') "
                      'ON CONFLICT(username) DO UPDATE SET '
                      'Password=excluded.Password, '
                      'Subdomain=excluded.Subdomain',
                      (secret['username'], password, secret['subdomain']))
            c.execute('INSERT INTO txt (Subdomain, LastUpdate) VALUES(?, 0)',
                      (secret['subdomain'],))
            conn.commit()
        except sqlite3.DatabaseError as exc:
            print('Database error: %s' % str(exc))


if __name__ == "__main__":
    import sys
    ret = entrypoint()
    sys.exit(ret)
