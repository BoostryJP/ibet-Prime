FROM python:3.8.7-alpine3.13

# make application directory
RUN mkdir -p /app/ibet-Prime/

# install packages
RUN apk update \
 && apk add --no-cache --virtual .build-deps \
      make \
      gcc \
      musl-dev \
      postgresql-dev \
      libffi-dev \
      autoconf \
      automake \
      libtool \
      curl

# add apl user/group
# NOTE: '/bin/bash' was added when 'libtool' installed.
RUN addgroup -g 1000 apl \
 && adduser -G apl -D -s /bin/bash -u 1000 apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app

# Python requirements
USER apl
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools \
 && pip install -r /app/requirements.txt \
 && rm -f /app/requirements.txt \
 && echo 'export LANG=ja_JP.utf8' >> ~/.bash_profile \
 && echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bash_profile

# app deploy
COPY --chown=apl:apl LICENSE /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/bin/
COPY --chown=apl:apl bin/ /app/ibet-Prime/bin/
RUN mkdir -p /app/ibet-Prime/contracts/
COPY --chown=apl:apl contracts/ /app/ibet-Prime/contracts/
RUN mkdir -p /app/ibet-Prime/conf/
COPY --chown=apl:apl conf/ /app/ibet-Prime/conf/
COPY --chown=apl:apl config.py server.py /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/batch/
COPY --chown=apl:apl batch/ /app/ibet-Prime/batch/
RUN mkdir -p /app/ibet-Prime/app/
COPY --chown=apl:apl app/ /app/ibet-Prime/app/
RUN find /app/ibet-Prime/ -type d -name __pycache__ | xargs rm -fr \
 && chmod -R 755 /app/ibet-Prime/

# command deploy
COPY --chown=apl:apl run.sh healthcheck.sh /app/

EXPOSE 5000
CMD /app/run.sh
HEALTHCHECK --interval=10s CMD /app/healthcheck.sh