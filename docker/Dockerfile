FROM ubuntu:14.04
RUN apt-get update
RUN apt-get install -y apt-transport-https

RUN apt-get install -y man
RUN apt-get install -y vim
RUN apt-get install -y python python-webob python-paste python-pastedeploy python-pastescript python-tz python-apt
RUN apt-get install -y python-sqlalchemy

RUN sudo apt-get install -y postgresql 
RUN sudo apt-get install -y python-psycopg2
RUN sudo apt-get install -y python-dateutil
RUN sudo apt-get install -y python-pip
RUN sudo addgroup wheel
ADD sudoers /etc/sudoers
RUN sudo useradd -p palette -ms /bin/bash palette
RUN sudo usermod -aG wheel palette

USER palette
WORKDIR /home/palette/
ADD install.sh /home/palette/
Add akiri.framework_0.5.6_all.deb /home/palette/

RUN sudo pip install webob
RUN sudo dpkg -i akiri.framework_0.5.6_all.deb
# RUN apt-get install -y curl
EXPOSE 443

# Make sure PostgreSQL is running and start bash
# ENTRYPOINT service postgresql restart && bash
