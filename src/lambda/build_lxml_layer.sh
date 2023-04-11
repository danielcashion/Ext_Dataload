#!/bin/bash

# Create virtualenv
virtualenv v-env
source v-env/bin/activate

# Install required packages
pip install lxml

# Deactivate virtualenv
deactivate

# Create directory for packages
mkdir python

# Copy packages to directory
cp -a ./v-env/lib/python3.7/site-packages/. ./python

# Create zip file
zip -r9 /outputs/lxml_layer.zip python
