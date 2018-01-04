#!/bin/bash

cd `dirname $0`

if [ $# -ne 1 ]; then
	echo "[Usage] $0 <output file>"
fi

./scanir $1 25
