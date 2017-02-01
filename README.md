[![Build Status](https://travis-ci.org/palette-software/palette-insight.svg?branch=master)](https://travis-ci.org/palette-software/palette-insight)

Licensing Server Code
=====================

Important note
--------------

Licensing is _disabled_ in the latest version of the Palette Software components.

Installation steps
-----------------

Database Setup:

```bash
sudo apt-get install -y postgresql python-psycopg2 python-dateutil python-pip
sudo -u postgres createuser --superuser palette
sudo -u postgres createuser --superuser $USER
sudo -u postgres createdb licensedb
```

Set the password for palette:

```bash
    sudo -u postgres psql
    postgres=# \password palette
    Enter new password: <yourpass>
    Enter it again:
    postgres=# \quit
```

Running licensing locally
-------------------------

```bash
# add/replace this line in /etc/hosts
127.0.0.1	localhost	licensing.palette-software.com

sudo ./application.wsgi --port=443 --pem=\*
```
