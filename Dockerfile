FROM pypy:latest
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
CMD [ "pypy3", "./mrun.py" ]
