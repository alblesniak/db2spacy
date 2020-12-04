FROM ubuntu:20.04

# Change working directory
RUN mkdir src
WORKDIR "/db2spacy"
COPY . .

# # Update packages and install dependency packages for Ubuntu
RUN apt-get update && apt-get upgrade -y && apt-get autoremove -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common -y
RUN DEBIAN_FRONTEND=noninteractive add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y \
    build-essential \
    libssl-dev \
    libpq-dev \
    libcurl4-gnutls-dev \
    libexpat1-dev \
    libxft-dev \
    chrpath \
    libfreetype6 \
    libfreetype6-dev \
    libfontconfig1 \
    libfontconfig1-dev \
    wget \
    curl \
    python3.8 \
    python3-setuptools \
    python3-pip \
    python3-dev \
    python3-venv \
    python3-urllib3 \
    git

# PIP
RUN pip3 -q install pip --upgrade

# MORFEUSZ
RUN apt-key adv --fetch-keys http://download.sgjp.pl/apt/sgjp.gpg.key \
    && apt-add-repository http://download.sgjp.pl/apt/ubuntu \
    && apt-get install -y morfeusz2 \
    && apt-get update \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install http://download.sgjp.pl/morfeusz/20201129/Linux/20.04/64/morfeusz2-1.9.16-cp38-cp38-linux_x86_64.whl

# SPACY and pl_spacy_model_morfeusz
RUN pip3 install -U spacy==2.2
RUN pip3 install "http://zil.ipipan.waw.pl/SpacyPL?action=AttachFile&do=get&target=pl_spacy_model_morfeusz-0.1.3.tar.gz"
RUN pip3 install 'h5py<3.0.0'