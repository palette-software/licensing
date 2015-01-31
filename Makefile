include pylint.mk
PEM := ~/.ssh/PaletteStandardKeyPair2014-02-16.pem
URL := ubuntu@licensing.palette-software.com

all: pylint
.PHONY: all

pylint:
	$(PYLINT) application.wsgi
	$(PYLINT) licensing.py
	$(PYLINT) create-table
	$(PYLINT) start-trial
.PHONY: pylint


publish:
	scp -i $(PEM) application.wsgi licensing.py $(URL):/opt/palette/
	scp -i $(PEM) license-start start-trial create-table $(URL):/tmp
	ssh -i $(PEM) $(URL) sudo mv /tmp/license-start /tmp/start-trial /tmp/create-table /usr/local/bin/
	ssh -i $(PEM) $(URL) sudo service apache2 reload
.PHONY: publish
