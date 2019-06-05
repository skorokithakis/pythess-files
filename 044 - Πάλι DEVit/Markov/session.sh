# Recorded with the doitlive recorder
#doitlive shell: /usr/bin/fish
#doitlive prompt: {nl}{user.cyan.bold}@{hostname.blue}:{dir.green} $

#dilc: Don't wait until the end to ask questions.

#dilc: What is Machine Learning?

#dilc: What are Markov Chains?

#dilc: "Hello world." => H -> e -> l -> l -> o ->   -> w -> o -> r -> l -> d -> .

#dilc: We can do this at the sentence level too. Hello -> world

#dilc: We don't have to only look at one sample, either. ("Good", "morning") -> "that's"

#dilc: We can run it in reverse to generate output.

#dilc: Let's write some code!

```ipython
from markovify.chain import Chain
some_code = open("some_of_django.py").read()
import re
chain = Chain([re.split("(\W)", some_code)], 3)
generate_code = lambda: "".join(chain.walk())
print(generate_code())
some_code = some_code.replace("    ", "\t")
chain = Chain([re.split("(\W)", some_code)], 3)
print(generate_code())
# Let's go from ML to AI and write an ADVERSARIAL GENERATIVE MODEL!
# We're going to use black (HTTP mode) as the adversary.
import requests
def is_code_valid(code):
    """Validate a piece of code for well-formedness."""
    r = requests.post("http://localhost:45484", data=code.encode("utf8"))
    return r.status_code != 400


is_code_valid("some_valid_code = 1")
is_code_valid("invalid code wooo !@#$%%$")
import time
start = time.time()
for c in range(100000):
    if c % 100 == 0:
        print(f"Generated {c} candidates ({int(time.time() - start)} seconds)...")
    code = generate_code()
    if is_code_valid(code):
        print(code)
        break


# You may now add "AI expert" to your CV.
```
