#!/bin/bash

cd `dirname $0`

if [ $# -ne 1 ]; then
	echo "[Usage] $0 <input file>"
fi

./sendir $1 3 24
