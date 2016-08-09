Docker presentation for PyThess
===============================

Installation
------------

To run the presentation, you need some stuff from a Github repo that runs under
NPM and reveal.js and other crap. Better to just run it under Docker:

    docker build -t stavros/docker-presentation .
    docker run -v `pwd`:/presentation stavros/docker-presentation

The presentation will be in output/index.js.

License
-------

This presentation is released under CC-BY-SA.
