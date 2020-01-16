FROM python:3.5 AS builder

COPY generate.py /python_app/
COPY requirements.txt /python_app/
COPY templates /python_app/templates/

WORKDIR /python_app
RUN mkdir html
RUN pip install -r requirements.txt
RUN python generate.py

FROM nginx AS server
COPY --from=builder /python_app/html/dashboard.html /usr/share/nginx/html/index.html
