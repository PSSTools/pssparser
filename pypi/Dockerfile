FROM quay.io/pypa/manylinux2010_x86_64

RUN yum install -y libuuid-devel

# Install a JRE
RUN yum install -y java-1.8.0-openjdk-devel

RUN /opt/python/cp35-cp35m/bin/pip install cython wheel twine
RUN /opt/python/cp36-cp36m/bin/pip install cython wheel twine
RUN /opt/python/cp37-cp37m/bin/pip install cython wheel twine
RUN /opt/python/cp38-cp38/bin/pip install cython wheel twine
RUN /opt/python/cp39-cp39/bin/pip install cython wheel twine ivpm

CMD /pssparser/pypi/build.sh


