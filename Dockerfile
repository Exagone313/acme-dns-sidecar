FROM debian:bookworm-slim AS common
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	python3-virtualenv \
	&& rm -rf /var/lib/apt/lists/* \
	&& useradd -ms /bin/bash acmedns
USER acmedns
RUN python3 -m virtualenv -p python3 ~/virtualenv

FROM common AS build-common
RUN . ~/virtualenv/bin/activate \
	&& pip install poetry

FROM build-common AS build-requirements
COPY --chown=acmedns:acmedns pyproject.toml poetry.lock /src/
RUN cd /src \
	&& . ~/virtualenv/bin/activate \
	&& poetry export -f requirements.txt -o requirements.txt

FROM build-common AS build-wheel
COPY --chown=acmedns:acmedns . /src
RUN . ~/virtualenv/bin/activate \
	&& cd /src \
	&& poetry build -f wheel

FROM common
USER root
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh
USER acmedns
COPY --from=build-requirements /src/requirements.txt /
RUN . ~/virtualenv/bin/activate \
	&& pip install -r /requirements.txt
COPY --from=build-wheel /src/dist/*.whl /
RUN . ~/virtualenv/bin/activate \
	&& pip install /*.whl
USER root
RUN rm /requirements.txt /*.whl
USER acmedns
ENTRYPOINT ["/entrypoint.sh"]
