FROM node:latest
RUN apt-get update
RUN apt-get install -y wget zip
RUN npm install -g xy124/reveal-md
VOLUME /presentation
WORKDIR /presentation
CMD /presentation/build.sh
