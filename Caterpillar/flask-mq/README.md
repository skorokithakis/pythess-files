#Readme

Just in case you weren't there, you weren't paying attention to Stavros or you just forgot and you don't want Stavros to be mad about it.

Here are some dummy instructions on how to get this thing up & running:

- Install virtualenv if you haven't already: `pip install virtualenv`   
- Create a directory
- `cd` to the directory
- `virtualenv env` to save the pip libraries locally
- [Activate the virtualenv](http://virtualenv.readthedocs.org/en/latest/virtualenv.html#activate-script) depending on your shell (e.g. for fish: `. env/bin/activate.fish`)
- Install [Flask](http://flask.pocoo.org/) (`pip install flask` or `pip install -r requirements.txt`)
- Create a flask-my.py file and paste the code inside (e.g. `vi flask-my.py`)
- Run the server `python flask-mq.py`
- Head over to [http://127.0.0.1:5000](http://127.0.0.1:5000)

Cheers!
