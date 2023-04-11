#!/bin/bash
# uploadLambdaCode.sh
# Author: GMind LLC
# Date: 03/12/2020

AWS_PROFILE=clubsports

rm -Rf bin/*

mkdir bin/add-job
pip3 install --target ./bin/add-job requests==2.28.2
cp src/add-job.py bin/add-job
pushd bin/add-job
zip -r ../add-job-code.zip .
popd
aws lambda update-function-code --function-name "TMDataLoadSTAGING-add-job" --zip-file "fileb://bin/add-job-code.zip"
aws lambda update-function-code --function-name "TMDataLoadPROD-add-job" --zip-file "fileb://bin/add-job-code.zip"

mkdir bin/process-job
pip3 install --target ./bin/process-job requests==2.28.2
cp ./src/lambda/src/process-job.py bin/process-job
cp ./tourneymachine_scraper/crawler.py bin/process-job
pushd bin/process-job

chmod -R 755 .
zip -r ../process-job-code.zip .
popd

aws lambda update-function-code --function-name "TMDataLoadSTAGING-process-job" --zip-file "fileb://bin/process-job-code.zip"
aws lambda update-function-code --function-name "TMDataLoadPROD-process-job" --zip-file "fileb://bin/process-job-code.zip"

