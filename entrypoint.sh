#!/bin/bash

alembic upgrade head
python app/api/main.py