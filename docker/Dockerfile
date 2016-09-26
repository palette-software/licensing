FROM ubuntu:14.04
RUN apt-get update
#RUN apt-get install -y apt-transport-https

RUN sudo apt-get install -y postgresql python-psycopg2 python-dateutil python-pip
RUN sudo addgroup wheel
ADD sudoers /etc/sudoers
RUN sudo useradd -p palette -ms /bin/bash palette
# RUN sudo usermod -aG sudo palette
RUN sudo usermod -aG wheel palette

# # Start PostgreSQL service on container startup
# CMD postgresql start

# RUN sudo -u postgres createuser --superuser palette
# RUN sudo -u postgres createdb licensedb

# Make sure PostgreSQL is running and start bash
ENTRYPOINT service postgresql restart && bash
