FROM ubuntu:24.04 AS builder

ENV PYTHON_VERSION=3.13.7
ENV UV_VERSION=0.6.5
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_INSTALL_DIR="/usr/local/bin"
ENV UV_PROJECT_ENVIRONMENT="/home/apl/.venv"

# make application directory
RUN mkdir -p /app

# add apl user/group
RUN userdel -r ubuntu \
 && groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app \
 && mkdir /home/apl \
 && chown -R apl:apl /home/apl

# install packages
RUN apt-get update -q \
 && apt-get upgrade -qy \
 && apt-get install -y --no-install-recommends \
 build-essential \
 ca-certificates \
 curl \
 libffi-dev \
 libpq-dev \
 libc-bin \
 clang \
 && apt clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install uv
ADD https://astral.sh/uv/$UV_VERSION/install.sh /uv-installer.sh
RUN INSTALLER_NO_MODIFY_PATH=1 sh /uv-installer.sh && rm /uv-installer.sh

# install Python
RUN uv python install $PYTHON_VERSION

# prepare venv
USER apl
RUN mkdir /home/apl/.venv

# setup shell setting
#   .bash_profile
RUN echo 'if [ -f ~/.bashrc ]; then' >> ~/.bash_profile && \
    echo '    . ~/.bashrc' >> ~/.bash_profile && \
    echo 'fi' >> ~/.bash_profile
#   .bashrc
RUN echo '. $HOME/.venv/bin/activate' >> ~apl/.bashrc

# install python packages
COPY --chown=apl:apl LICENSE /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/bin/
COPY --chown=apl:apl bin/ /app/ibet-Prime/bin/
RUN mkdir -p /app/ibet-Prime/cmd/
COPY --chown=apl:apl cmd/ /app/ibet-Prime/cmd/
RUN mkdir -p /app/ibet-Prime/contracts/
COPY --chown=apl:apl contracts/ /app/ibet-Prime/contracts/
RUN mkdir -p /app/ibet-Prime/conf/
COPY --chown=apl:apl conf/ /app/ibet-Prime/conf/
COPY --chown=apl:apl config.py eth_config.py run.py server.py alembic.ini /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/migrations/
COPY --chown=apl:apl migrations/ /app/ibet-Prime/migrations/
RUN mkdir -p /app/ibet-Prime/batch/
COPY --chown=apl:apl batch/ /app/ibet-Prime/batch/
RUN mkdir -p /app/ibet-Prime/app/
COPY --chown=apl:apl app/ /app/ibet-Prime/app/
RUN find /app/ibet-Prime/ -type d -name __pycache__ | xargs rm -fr \
 && chmod -R 755 /app/ibet-Prime/

COPY pyproject.toml /app/ibet-Prime/pyproject.toml
COPY uv.lock /app/ibet-Prime/uv.lock
RUN cd /app/ibet-Prime \
 && uv venv $UV_PROJECT_ENVIRONMENT \
 && uv sync --frozen --no-dev --no-install-project --all-extras \
 && rm -f /app/ibet-Prime/pyproject.toml \
 && rm -f /app/ibet-Prime/uv.lock

FROM ubuntu:24.04 AS runner

# make application directory
RUN mkdir -p /app/ibet-Prime/

# add apl user/group
RUN userdel -r ubuntu \
 && groupadd -g 1000 apl \
 && useradd -g apl -s /bin/bash -u 1000 -p apl apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app \
 && mkdir /home/apl \
 && chown -R apl:apl /home/apl

# install packages
RUN apt-get update -q \
  && apt-get upgrade -qy \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  libssl-dev \
  libpq-dev \
  language-pack-ja-base \
  language-pack-ja \
  jq \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# copy python, dependencies and uv from builder stage
USER apl
COPY --from=builder --chown=apl:apl /home/apl/ /home/apl/
COPY --from=builder --chown=apl:apl /app/ibet-Prime/ /app/ibet-Prime/
COPY --from=builder --chown=apl:apl /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder --chown=apl:apl /usr/local/bin/uvx /usr/local/bin/uvx

ENV LANG=ja_JP.utf8
ENV UV_PROJECT_ENVIRONMENT="/home/apl/.venv"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/ibet-Prime:/app/ibet-Prime/cmd

COPY run.sh healthcheck.sh /app/

EXPOSE 5000
CMD ["/app/run.sh"]
HEALTHCHECK --interval=10s CMD ["/app/healthcheck.sh"]