#!/bin/bash
pkexec env DISPLAY=$DISPLAY \
    XAUTHORITY=$XAUTHORITY \
    PYTHONPATH=/home/reekid/Downloads/macro/.venv/lib/python3.12/site-packages \
    /home/reekid/Downloads/macro/.venv/bin/python3.12 /home/reekid/Downloads/macro/macro_app.py 