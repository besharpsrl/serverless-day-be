FROM lambci/lambda:build-python3.6
RUN mkdir /mydoctransfer-lambda
WORKDIR /mydoctransfer-lambda
CMD pip3.6 install -r /mydoctransfer-lambda/requirements.txt && chalice local --host=0.0.0.0

