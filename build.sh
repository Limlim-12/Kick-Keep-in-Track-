#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

flask db upgrade
flask seed-db # Run our seeder command after migrations