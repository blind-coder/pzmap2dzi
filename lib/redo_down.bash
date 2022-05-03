#!/bin/bash -u

base="${1}"
level="${2}"
xmin="${3}"
xmax="${3}"
ymin="${4}"
ymax="${4}"
format="${5:-png}"
while [ -d "${base}/${level}" ]; do
	for x in $(seq ${xmin} ${xmax}); do
		for y in $(seq ${ymin} ${ymax}); do
			rm -v ${base}/${level}/${x}_${y}.${format}
		done
	done
	xmin=$((xmin*2))
	xmax=$((xmax*2+1))
	ymin=$((ymin*2))
	ymax=$((ymax*2+1))
	level=$((level+1))
done
