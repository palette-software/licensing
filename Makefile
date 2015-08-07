export PYTHONPATH=.

include pylint.mk
PEM := ~/.ssh/PaletteStandardKeyPair2014-02-16.pem
URL := ubuntu@licensing.palette-software.com

FILES := application.wsgi \
	licensing.py \
        license_manager.py \
	mixin.py \
	salesforce_api.py \
	sendwithus_api.py \
	slack_api.py \
	ansible_api.py \
	boto_api.py \
	support.py \
	stage.py \
	plan.py \
        product.py \
        server_info.py \
	register.py \
	subscribe.py \
	system.py \
	utils.py

SCRIPTS := \
	support-connect \
	support-define-port \
	license-cleanup \
        license-create \
	license-sync \
        license-update

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

publish_scripts:
	scp -i $(PEM) scripts/create-tables $(URL):/opt/palette/
	cd scripts && scp -i $(PEM) $(SCRIPTS) $(URL):/tmp
	ssh -i $(PEM) $(URL) sudo mv /tmp/license-\* /tmp/support-\* /usr/local/bin/
.PHONY: publish_scripts

publish: publish_scripts
	scp -i $(PEM) $(FILES) $(URL):/opt/palette/
	ssh -i $(PEM) $(URL) sudo service apache2 reload
.PHONY: publish

