FROM python:3.9
WORKDIR /app
COPY ./requirements.txt ./requirements.txt
COPY ./model.pkl ./model.pkl
RUN pip install --no-cache-dir --upgrade -r ./requirements.txt
COPY ./app.py .
COPY ./test.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "1313"]