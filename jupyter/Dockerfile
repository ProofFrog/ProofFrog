FROM python:3.11

WORKDIR /app

COPY ./ /app

RUN pip install --no-cache-dir -r ./requirements.txt
RUN pip install notebook
RUN jupyter kernelspec install jupyter/kernel

EXPOSE 8888

CMD ["jupyter", "notebook", "--notebook-dir=jupyter/example", "--ip='0.0.0.0'", "--port=8888", "--no-browser", "--allow-root"]
