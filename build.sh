#!/bin/bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cd mydoctransfer-lambda

#/root/.local/bin/pytest

#if [[ $? -ne 0 ]] ; then
#    exit 1
#fi

/root/.local/bin/chalice deploy
