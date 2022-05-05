FROM python:3.10.4-buster

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

RUN mkdir -p /usr/local/nvm
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 16.14.2

# install nvm
# https://github.com/creationix/nvm#install-script
RUN curl --silent -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash

# install node and npm
RUN . $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

# add node and npm to path so the commands are available
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# confirm installation
RUN node -v
RUN npm -v


RUN sed -i 's/archive.ubuntu.com/ftp.daumkakao.com/g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -yq \
        tzdata \
        locales locales-all \
        ca-certificates \
        libappindicator1 libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 \
        gconf-service lsb-release wget xdg-utils \
        fonts-liberation \
        fonts-freefont-ttf \
        fonts-nanum* \
        libgbm-dev \
    && locale-gen ko_KR.UTF-8 \
    && /usr/sbin/update-locale LANG=ko_KR.UTF-8 \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# 한글 폰트
# RUN mkdir /usr/share/fonts/nanumfont \
#     && wget http://cdn.naver.com/naver/NanumFont/fontfiles/NanumFont_TTF_ALL.zip \
#     && unzip NanumFont_TTF_ALL.zip -d /usr/share/fonts/nanumfont \
#     && fc-cache -f -v

RUN adduser app
USER app
WORKDIR /home/app

# Set the lang
ENV LC_ALL ko_KR.UTF-8
ENV LNGUAGE ko_KR.UTF-8
ENV LANG ko_KR.UTF-8
ENV PYTHONIOENCODING UTF-8

ENV PUPPETEER_PRODUCT firefox
RUN npm install percollate puppeteer-cli --unsafe-perm=true
ENV PATH="/home/app/node_modules/.bin:${PATH}"

ENV PYTHONPATH /home/app
ENV PATH="/home/app/.local/bin:${PATH}"

COPY --chown=app:app requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY --chown=app:app . .

# RUN pytest -v ./tests
CMD python pdfthis.py
