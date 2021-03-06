#!/bin/bash
# clones/updates the elife api-raml repository
# this repository contains the specification for article-json and
# is used to validate what the scraper generates.
# see `src/validate.py`

set -e # everything must pass
cd schema
if [ ! -d api-raml ]; then
    git clone https://github.com/elifesciences/api-raml
fi
cd ..

if [ -f api-raml.sha1 ]; then
    cd schema/api-raml
    # existing api-raml shallow clones, containing only 1 commit
    git reset --hard
    git fetch origin
    git checkout "$(cat ../../api-raml.sha1)"
    cd -
fi
