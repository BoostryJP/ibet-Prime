FROM ubuntu:22.04

# make application directory
RUN mkdir -p /app/ibet-Prime/

# add apl user/group
RUN groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app

# install packages
RUN apt-get update -q \
 && apt-get upgrade -qy \
 && apt-get install -y --no-install-recommends \
 unzip \
 build-essential \
 ca-certificates \
 curl \
 libbz2-dev \
 libreadline-dev \
 libsqlite3-dev \
 libssl-dev \
 zlib1g-dev \
 libffi-dev \
 python3-dev \
 libpq-dev \
 automake \
 pkg-config \
 libtool \
 libgmp-dev \
 language-pack-ja-base \
 language-pack-ja \
 git \
 libyaml-cpp-dev \
 libc-bin \
 liblzma-dev

# remove unnessesory package files
RUN apt clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install pyenv
RUN git clone https://github.com/pyenv/pyenv.git /home/apl/.pyenv
RUN chown -R apl:apl /home/apl

USER apl
RUN echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~apl/.bash_profile \
 && echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~apl/.bash_profile \
 && echo 'eval "$(pyenv init --path)"' >> ~apl/.bash_profile \
 && echo 'export LANG=ja_JP.utf8' >> ~apl/.bash_profile

# install python
USER apl
RUN . ~/.bash_profile \
 && pyenv install 3.12.2 \
 && pyenv global 3.12.2 \
 && pip install --upgrade pip setuptools

# install poetry
RUN . ~/.bash_profile \
 && python -m pip install poetry==1.8.2
RUN . ~/.bash_profile \
 && poetry config virtualenvs.create false \
 && poetry config installer.max-workers 1

# install python packages
USER root
COPY --chown=apl:apl LICENSE /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/bin/
COPY --chown=apl:apl bin/ /app/ibet-Prime/bin/
RUN mkdir -p /app/ibet-Prime/cmd/
COPY --chown=apl:apl cmd/ /app/ibet-Prime/cmd/
RUN mkdir -p /app/ibet-Prime/contracts/
COPY --chown=apl:apl contracts/ /app/ibet-Prime/contracts/
RUN mkdir -p /app/ibet-Prime/conf/
COPY --chown=apl:apl conf/ /app/ibet-Prime/conf/
COPY --chown=apl:apl config.py server.py alembic.ini /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/migrations/
COPY --chown=apl:apl migrations/ /app/ibet-Prime/migrations/
RUN mkdir -p /app/ibet-Prime/batch/
COPY --chown=apl:apl batch/ /app/ibet-Prime/batch/
RUN mkdir -p /app/ibet-Prime/app/
COPY --chown=apl:apl app/ /app/ibet-Prime/app/
RUN find /app/ibet-Prime/ -type d -name __pycache__ | xargs rm -fr \
 && chmod -R 755 /app/ibet-Prime/

USER apl
COPY pyproject.toml /app/ibet-Prime/pyproject.toml
COPY poetry.lock /app/ibet-Prime/poetry.lock
RUN . ~/.bash_profile \
 && cd /app/ibet-Prime \
 && poetry install --only main --no-root --all-extras \
 && rm -f /app/ibet-Prime/pyproject.toml \
 && rm -f /app/ibet-Prime/poetry.lock
ENV PYTHONPATH /app/ibet-Prime:/app/ibet-Prime/cmd

# command deploy
USER apl
COPY run.sh healthcheck.sh /app/

EXPOSE 5000
CMD /app/run.sh
HEALTHCHECK --interval=10s CMD /app/healthcheck.sh