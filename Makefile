include pylint.mk
PEM := ~/.ssh/PaletteStandardKeyPair2014-02-16.pem
URL := ubuntu@licensing.palette-software.com

FILES := application.wsgi licensing.py support.py
SCRIPTS := \
	license-start \
	license-start-trial \
	support-connect \
	support-define-port

all: pylint
.PHONY: all

pylint:
	for x in $(FILES); do \
		$(PYLINT) $$x; \
	done
	for x in $(SCRIPTS); do \
		$(PYLINT) scripts/$$x; \
	done
.PHONY: pylint

publish:
	scp -i $(PEM) $(FILES) $(URL):/opt/palette/
	cd scripts && scp -i $(PEM) $(SCRIPTS) $(URL):/tmp
	scp -i $(PEM) scripts/create-tables $(URL):
	ssh -i $(PEM) $(URL) sudo mv /tmp/license-\* /tmp/support-\* /usr/local/bin/
	ssh -i $(PEM) $(URL) sudo service apache2 reload
.PHONY: publish

