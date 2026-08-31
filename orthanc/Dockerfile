FROM orthancteam/orthanc:25.11.2
LABEL Author="Guillaume Theaud"
LABEL Description="Orthanc, free DICOM server, with OHIF"

RUN apt-get update
RUN apt-get install -y apt-transport-https ca-certificates curl software-properties-common
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
RUN add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
RUN apt-get update
RUN apt-get install -y docker.io

RUN pip3 install Jinja2==3.1.4 --break-system-packages
