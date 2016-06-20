<img src="img/logo.png" style="float: left" />

## Deploying an app on Docker

### and other stories

A [PyThess](https://www.meetup.com/PyThess/) presentation by [@stavros](https://www.twitter.com/stavros)

---

# Introduction

---

## What is Docker?

Docker is a lightweight way of running processes in isolated containers.

<dl>

<dt class="fragment" data-fragment-index="1">*How Docker is like a VM*</dt>
<dd class="fragment" data-fragment-index="1">
<ul>
    <li>Runs things self-containedly.</li>
    <li>Processes see their own (file)system.</li>
</ul>
</dd>

<dt class="fragment" data-fragment-index="2">*How Docker is not like a VM*</dt>
<dd class="fragment" data-fragment-index="2">
<ul>
    <li>Only runs one process (yes I know shut up).</li>
    <li>Does not allocate extra memory.</li>
    <li>No performance hit.</li>
</ul>
</dd>

</dl>

---

## Basic concepts

<dl>

<dt class="fragment" data-fragment-index="1">*Image*</dt>
<dd class="fragment" data-fragment-index="1">
A layered set of files.
</dd>

<dt class="fragment" data-fragment-index="2"><strong>Container</strong></dt>
<dd class="fragment" data-fragment-index="2">
An instance of an *image* that can be run, with its session-related files.
</dd>

<dt class="fragment" data-fragment-index="3"><strong>Dockerfile</strong></dt>
<dd class="fragment" data-fragment-index="3">
Instructions for creating an *image*.
</dd>

<dt class="fragment" data-fragment-index="4"><strong>Docker-Compose</strong></dt>
<dd class="fragment" data-fragment-index="4">
Instructions for tying *containers* together.
</dd>

</dl>

---

## Django deployment basics

When deploying a Django application, we need:

* `pip install -Ur requirements.txt`
* `manage.py migrate`
* `manage.py runserver`

---

## Our Dockerfile

```
FROM python:latest
RUN apt-get update
RUN apt-get install -y swig libssl-dev dpkg-dev
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -Ur requirements.txt
```

---

## Spinning up a virtual stack

<p class="fragment" data-fragment-index="1">
To deploy a complete application, we don't just need a single container, we need
databases, app servers, web servers, cache servers, etc.
</p>

<p class="fragment" data-fragment-index="2">
We can do this using Docker-Compose.
</p>

<p class="fragment" data-fragment-index="3">
Docker-Compose (*née* fig) is a way to connect containers to each other and spin
them up together, as required.
</p>

---

## Our Docker-Compose file

```
version: '2'
services:
  db:
    image: postgres
    environment:
      POSTGRES_PASSWORD: password
    volumes:
      - ./dbdata:/var/lib/postgresql/data
  web:
    command: python manage.py runserver
    image: pastery
    build: .
    volumes:
      - .:/code
    depends_on:
      - db
```

---

# Hands-on example

---

# Questions?

---

# Thank you!
