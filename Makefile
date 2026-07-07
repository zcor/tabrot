# tabrot — install, test, and package. See docs/superpowers/specs/ for design.
SHELL := /bin/bash

VERSION := $(shell sed -n 's/^TABROT_VERSION="\(.*\)"/\1/p' tabrot)

PREFIX  ?= /usr/local
BINDIR   = $(PREFIX)/bin
SHAREDIR = $(PREFIX)/share/tabrot

.PHONY: all test lint install uninstall dist deb clean

all: test

test:
	python3 tests/test_parser.py
	tests/test_cli.sh

lint:
	shellcheck tabrot tests/test_cli.sh

install:
	install -d "$(DESTDIR)$(BINDIR)" "$(DESTDIR)$(SHAREDIR)/templates"
	install -m 0755 tabrot "$(DESTDIR)$(BINDIR)/tabrot"
	install -m 0644 src/snss_tabs.py "$(DESTDIR)$(SHAREDIR)/snss_tabs.py"
	install -m 0644 TRIAGE.md "$(DESTDIR)$(SHAREDIR)/TRIAGE.md"
	install -m 0644 templates/PARKED.template.md "$(DESTDIR)$(SHAREDIR)/templates/PARKED.template.md"

uninstall:
	rm -f "$(DESTDIR)$(BINDIR)/tabrot"
	rm -rf "$(DESTDIR)$(SHAREDIR)"

dist:
	mkdir -p dist
	git archive --format=tar.gz --prefix=tabrot-$(VERSION)/ -o dist/tabrot-$(VERSION).tar.gz HEAD

deb:
	@command -v dpkg-deb >/dev/null 2>&1 || { echo "make deb requires dpkg-deb (run on Debian/Ubuntu or in CI)." >&2; exit 1; }
	rm -rf build/debroot
	$(MAKE) install DESTDIR=build/debroot PREFIX=/usr
	install -d build/debroot/DEBIAN build/debroot/usr/share/doc/tabrot
	sed 's/{{VERSION}}/$(VERSION)/' packaging/deb/control.in > build/debroot/DEBIAN/control
	install -m 0644 packaging/deb/copyright build/debroot/usr/share/doc/tabrot/copyright
	mkdir -p dist
	dpkg-deb --build --root-owner-group build/debroot dist/tabrot_$(VERSION)_all.deb

clean:
	rm -rf build dist
