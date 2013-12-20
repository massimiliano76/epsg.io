#!/bin/bash
echo Content-type: text/plain
echo

cd /var/www/epsg.io/

echo $PWD
whoami

git pull
git status
git submodule sync
git submodule update
git submodule status

./gunicorn-epsgio reload

echo DONE