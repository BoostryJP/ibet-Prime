FROM python:3.8.7-alpine3.13

# make application directory
RUN mkdir -p /app/ibet-Prime/

# add apl user/group
RUN addgroup -g 1000 apl \
 && adduser -G apl -D -s /bin/ash -u 1000 apl \
 && echo 'apl ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && chown -R apl:apl /app

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
      libtool

# Python requirements
USER apl
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools \
 && pip install -r /app/requirements.txt \
 && rm -f /app/requirements.txt \
 && echo 'export LANG=ja_JP.utf8' >> ~/.profile \
 && echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.profile

# app deploy
COPY LICENSE /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/bin/
COPY bin/ /app/ibet-Prime/bin/
RUN mkdir -p /app/ibet-Prime/contracts/
COPY contracts/ /app/ibet-Prime/contracts/
RUN mkdir -p /app/ibet-Prime/conf/
COPY conf/ /app/ibet-Prime/conf/
COPY config.py /app/ibet-Prime/
RUN mkdir -p /app/ibet-Prime/batch/
COPY batch/ /app/ibet-Prime/batch/
RUN mkdir -p /app/ibet-Prime/app/
COPY app/ /app/ibet-Prime/app/
RUN find /app/ibet-Primefind -d --name __pycache__ | xargs rm -fr

# command deploy
# TODO:make healthcheck.sh
#COPY run.sh healthcheck.sh /app/
COPY run.sh /app/

EXPOSE 8000
CMD /app/run.sh
# TODO:healthcheck.sh execute
#HEALTHCHECK --interval=10s CMD /app/healthcheck.sh