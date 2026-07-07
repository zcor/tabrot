# tabrot — install, test, and package. See docs/superpowers/specs/ for design.
SHELL := /bin/bash

VERSION := $(shell sed -n 's/^TABROT_VERSION="\(.*\)"/\1/p' tabrot)

PREFIX  ?= /usr/local
BINDIR   = $(PREFIX)/bin
SHAREDIR = $(PREFIX)/share/tabrot

.PHONY: all test lint install uninstall dist clean

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

clean:
	rm -rf build dist
