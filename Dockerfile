FROM python:3.7-slim
LABEL author='mkhvdm@gmail.com' version=0.1
RUN mkdir /nasa_pic_app
WORKDIR /nasa_pic_app
COPY . .
RUN pip3 install -r requirements.txt --no-cache-dir

CMD ["python3", "bot.py" ]