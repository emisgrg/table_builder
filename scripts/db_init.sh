#!/bin/bash

set -e

echo "CREATE DATABASE table_builder ENCODING 'UTF8';" | psql -U postgres -h localhost -p 5432
