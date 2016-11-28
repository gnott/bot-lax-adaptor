#!/bin/bash
# feeds articles in the `./article-xml` directory into lax
set -e # everything must pass
. install.sh
. download-elife-xml.sh

args="$@"
python src/adaptor.py $args
