psql -c 'CREATE ROLE mecha3 LOGIN CREATEDB' -U postgres -h db
psql -c 'CREATE DATABASE mecha3 WITH OWNER = mecha3' -U postgres -h db
curl -L https://codeclimate.com/downloads/test-reporter/test-reporter-latest-linux-amd64 > ./cc-test-reporter
chmod +x ./cc-test-reporter
./cc-test-reporter before-build
pytest -v --cov --cov-report xml --junit-xml=test-reports
./cc-test-reporter after-build --coverage-input-type coverage.py --exit-code $?