#!/bin/sh

if [ ! -d "output" ]; then
    wget https://codeload.github.com/hakimel/reveal.js/zip/master
    unzip master
    mv reveal.js-master output
    rm master
fi
echo "Generating presentation..."
reveal-md presentation.md --theme league --static > output/index.html
cp -R img output/
