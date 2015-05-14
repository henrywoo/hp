#!/bin/bash
x=1

while [ 2 -ge 1 ]
do
  echo "hello world $x"
  x=$(($x + 1))
  sleep 1
done
