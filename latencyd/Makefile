RPMDIR := $(HOME)/rpmbuild

PACKAGE_NAME = latencyd
PACKAGE_VERSION = 1.0.0
PACKAGE_SOURCES = $(wildcard *.go)

all: $(PACKAGE_NAME)

$(PACKAGE_NAME): $(PACKAGE_SOURCES)
	go build -x -ldflags="-s -w" -o $@ $^

$(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz: $(PACKAGE_NAME)
	install -d $(PACKAGE_NAME)-$(PACKAGE_VERSION)
	install -m 0755 $(PACKAGE_NAME) $(PACKAGE_NAME)-$(PACKAGE_VERSION)/$(PACKAGE_NAME)
	tar -c -z -f $@ $(PACKAGE_NAME)-$(PACKAGE_VERSION)/
	rm -rvf $(PACKAGE_NAME)-$(PACKAGE_VERSION)

clean:
	rm -vf $(PACKAGE_NAME)

rpm: $(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz
	mkdir -v -p $(RPMDIR)/{SPECS,SOURCES}
	install \
		$(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz \
		$(RPMDIR)/SOURCES/$(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz
	install \
		$(PACKAGE_NAME).service \
		$(RPMDIR)/SOURCES/$(PACKAGE_NAME).service
	rpmbuild -bb $(PACKAGE_NAME).spec

.PHONY: all clean rpm
