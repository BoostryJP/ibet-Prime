FROM ubuntu:20.04

# make application directory
RUN mkdir -p /app/ibet-Prime/

# add apl user/group
RUN groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app

# install packages
RUN apt-get update -q \
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
 libyaml-cpp-dev

# remove unnessesory package files
RUN apt clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install pyenv
RUN git clone https://github.com/pyenv/pyenv.git /home/apl/.pyenv
RUN chown -R apl:apl /home/apl

USER apl
RUN echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~apl/.bash_profile \
 && echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~apl/.bash_profile \
 && echo 'eval "$(pyenv init -)"' >> ~apl/.bash_profile \
 && echo 'export LANG=ja_JP.utf8' >> ~apl/.bash_profile

# install python
USER apl
RUN . ~/.bash_profile \
 && pyenv install 3.8.7 \
 && pyenv global 3.8.7 \
 && pip install --upgrade pip

# install python packages
USER apl
COPY requirements.txt /app/requirements.txt
RUN . ~/.bash_profile \
 && pip install -r /app/requirements.txt \
 && rm -f /app/requirements.txt

# app deploy
USER root
COPY --chown=apl:apl LICENSE /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/bin/
COPY --chown=apl:apl bin/ /app/ibet-Prime/bin/
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

# test build layer
USER root
RUN mkdir -p /app/ibet-Prime/tests/
COPY --chown=apl:apl tests/ /app/ibet-Prime/tests/
RUN chmod -R 755 /app/ibet-Prime/tests/

USER apl
RUN mkdir -p /app/ibet-Prime/cov/
RUN . ~/.bash_profile \
 && pip install -r /app/ibet-Prime/tests/requirements.txt

CMD /app/ibet-Prime/tests/qa.sh