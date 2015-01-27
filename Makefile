PEM := ~/.ssh/PaletteStandardKeyPair2014-02-16.pem
URL := ubuntu@licensing.palette-software.com

all:
	@echo Run \'make publish\' instead.
	@exit 1
.PHONY: all

publish:
	scp -i $(PEM) application.wsgi $(URL):/opt/palette/
	ssh -i $(PEM) $(URL) sudo service apache2 reload
.PHONY: publish
