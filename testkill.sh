#! /bin/sh

kill -9 `ps fax | grep tpsai-py | grep -v grep | sed -e's/ .*//'`
