#!/usr/bin/env python

from collections import defaultdict
import datetime

from flask import Flask, request, jsonify
from flask.views import MethodView
app = Flask(__name__)


messages = defaultdict(list)

MAX_MESSAGES = 4


class Stream(MethodView):
    methods = ["GET", "POST"]

    def get(self, key):
        my_messages = messages[key]
        return jsonify({"messages": my_messages})

    def post(self, key):
        message = {
                "name": key,
                "timestamp": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                "value": request.form
                }

        my_messages = messages[key]
        my_messages.append(message)
        if len(my_messages) > MAX_MESSAGES:
            messages[key] = my_messages[1:MAX_MESSAGES+1]
        return jsonify({"message": message})

@app.route("/")
def hello():
    return "Please read the documentation on how to use this awesome server!"

app.add_url_rule("/stream/<key>/", view_func=Stream.as_view("stream"))

if __name__ == "__main__":
    app.run(debug=True)
