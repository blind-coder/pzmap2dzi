#!/bin/bash -u

base="${1}"
level="${2}"
x="${3}"
y="${4}"
format="${5:-png}"
while [ -d "${base}/${level}" ]; do
	rm -v ${base}/${level}/${x}_${y}.${format}
	x=$((x/2))
	y=$((y/2))
	level=$((level-1))
done
