#!/bin/bash
base=$(dirname $0)
export PYTHONPATH=$(cd $base/.. && pwd)
exec python $base/tests.py
