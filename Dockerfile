FROM python3.13
RUN mkdir /app
WORKDIR /app
COPY main.py ./
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt
CMD ["python", "main.py"]