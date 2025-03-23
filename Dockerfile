FROM python:3
RUN mkdir /app
WORKDIR /app
COPY main.py ./
COPY requirements.txt ./
COPY modules/ ./modules/
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
CMD ["python", "main.py"]