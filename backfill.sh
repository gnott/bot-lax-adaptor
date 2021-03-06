#!/bin/bash
# the purpose of the bot-lax-adaptor project is to do the necessary data 
# wrangling of article data from the bot before sending it to lax. 
# this takes several forms:
# * listening to a queue for messages about which articles to process
# * processing directories of article xml from the filesystem
#
# this script is used to update the article-json stored in lax, performing just
# the ingestion of content - *no* PUBLISH events whatsoever.
#
# when pubdates need to be changed they must be issued as SILENT CORRECTIONS
# from the production workflow.

set -euo pipefail # strict mode

# by default we use the checkout of the `elife-article-xml` repository to ingest
# use `/some/other/dir/` as first param to ingest xml from another directory
default_dir="$(pwd)/articles-xml/articles/"
dir=${1:-$default_dir}

# by default we just send INGEST commands with `--ingest`
# use `--ingest+publish` as second param to also publish articles
# use with `--publish` as second param to publish any ingested by unpublished articles
default_action="--ingest"
action=${2:-$default_action}

trap ctrl_c INT
function ctrl_c() {
    echo "caught ctrl-c"
    exit 1
}

echo "backfill.sh

this script will:
1. pull latest article-xml from elifesciences/elife-article-xml
2. generate article-json from ALL xml in the ./articles-xml/articles/ directory
3. validate all article-json in the ./article-json/ directory
4. force an INGEST for all articles in the ./article-json/valid/ directory"

read -p "any key to continue (ctrl-c to quit) "

# import which dir of xmL?
if [ ! -z "$dir" ]; then
    # no dir passed through, assume default and update elife xml
    . download-elife-xml.sh
fi

# activate venv
set +o nounset; . install.sh; set -o nounset;

# this approach DOES NOT WORK WELL. it's possible, but *very* slow
# python ./src/adaptor.py --action ingest --force --type fs

# instead, run bulk lots: download, bulk generate, bulk ingest and skip the adaptor

. generate-article-json.sh
. validate-all-json.sh

lax="/srv/lax/"

# call the lax 'ingest' command with a directory of valid article json

# use a dir called 'patched' if you find it. 
# used for testing a subset of the full corpus
dir="$(pwd)/article-json/patched/"
#if [ -d patched ]; then
#   dir="$(pwd)/patched/"
#fi

time "$lax/manage.sh" ingest "$action" --force --dir "$dir" #(pwd)/article-json/patched/"

