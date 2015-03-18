include pylint.mk
PEM := ~/.ssh/PaletteStandardKeyPair2014-02-16.pem
URL := ubuntu@licensing.palette-software.com

FILES := application.wsgi \
	licensing.py \
	mixin.py \
	salesforce_api.py \
	sendwithus_api.py \
	slack_api.py \
	ansible_api.py \
	boto_api.py \
	support.py \
	stage.py \
	system.py \
	utils.py

SCRIPTS := \
	license-start \
	license-start-trial \
	support-connect \
	support-define-port \
	cleanup

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
	scp -i $(PEM) $(FILES) scripts/create-tables $(URL):/opt/palette/
	cd scripts && scp -i $(PEM) $(SCRIPTS) $(URL):/tmp
	scp -i $(PEM) scripts/create-tables $(URL):
	ssh -i $(PEM) $(URL) sudo mv /tmp/license-\* /tmp/support-\* /usr/local/bin/
	ssh -i $(PEM) $(URL) sudo service apache2 reload
.PHONY: publish

