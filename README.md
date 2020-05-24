# acme-dns-sidecar

Register in [acme-dns](https://github.com/joohoi/acme-dns) using Kubernetes secrets.

## Usage

* Create a container with [exagone313/acme-dns-sidecar](https://hub.docker.com/r/exagone313/acme-dns-sidecar) Docker image.
* Configure *acme-dns* to use `sqlite3` database engine.
* Mount *acme-dns* configuration file and database into that container.
* Create secrets in the same namespace with these keys:
    * `username`: a UUID ([RFC 4122](https://tools.ietf.org/html/rfc4122.html))
    * `password`: matches `^[-_A-Za-z0-9]{40}$`
    * `subdomain`: a valid subdomain name

Secret values not following the limitations introduced in *acme-dns* implementation will be ignored.

Tested with my own [acme-dns](https://hub.docker.com/r/exagone313/acme-dns) Docker image although official one should work too.

## Additional configuration options

To control which secrets are read by *acme-dns-sidecar*, you may add these keys to the configuration file.
This doesn't introduce any incompatibility with *acme-dns* as it doesn't read unknown configuration keys.

```toml
[sidecar.secrets]
# only secrets matching these patterns will be read
#field_selector = ""
#label_selector = ""
```

See also [config.cfg](config.cfg) for the list of options read by *acme-dns-sidecar*.

## Kubernetes deployment

A sample YAML file for deploying *acme-dns-sidecar* alongside *acme-dns* can be found in [acmedns.yml](acmedns.yml).

You need to make sure port 53 is not used on the host, typically by local resolvers bound on `127.0.0.53`.

## License

See [UNLICENSE](UNLICENSE).
