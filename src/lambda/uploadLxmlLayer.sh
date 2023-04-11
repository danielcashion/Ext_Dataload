docker run -v $(pwd)/src/lambda:/outputs -it lambci/lambda:build-python3.7 /bin/bash /outputs/build_lxml_layer.sh
