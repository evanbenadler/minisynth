minsynth
========

# Fork of Minisynth for a CS 6120 assignment

I attempted to extend Minisynth with floating point values and type coercion in
order to try to synthesize the John Carmack inverse square root hack based on a
five-iteration "blind" Newton Rhapson program. I extended all bit vectors to 32
bits and modified the goal Z3 expression to require both programs to be
approximately equal on all inputs, rather than completely equal.

The results were... inconclusive. If I require both programs to differ by at
most 0.1, Z3 fails in a couple of seconds. This is probably indicative of some
buggy behavior with the type coercion. However, I figured that perhaps the
quick square root inverse and the five-step newton square root inverse
legitimately differ by more than 0.1 on some inputs. I tried requiring them to
differ by at most 1, and I got a very similar result (i.e., quickly failing).
Next, I tried requiring them to differ by at most 10. This time, Z3 stalled for
over 15 minutes, and I ended up cancelling it.

Command: `python ex2.py < sketches/fast_inverse_sqrt.txt`

# Original Readme

These are supporting materials for a lecture on program synthesis in the [Sketch][] tradition.

Install [Z3][] with its Python 3 bindings. With Homebrew:

    $ brew install z3 --with-python

Install our only Python dependency, [Lark][]:

    $ pip3 install --user lark-parser

Witness the magic of Z3:

    $ python3 ex0.py

Run a simple example to see how to synthesize values, which is stolen from [Aws Albarghouthi][aws]'s [primer][]:

    $ python3 ex1.py

Run a more complete synthesis engine for a little arithmetic language:

    $ python3 ex2.py < sketches/s1.txt

[lark]: https://github.com/lark-parser/lark
[primer]: http://barghouthi.github.io/2017/04/24/synthesis-primer/
[aws]: http://www.cs.wisc.edu/~aws
[sketch]: https://people.csail.mit.edu/asolar/papers/thesis.pdf
[z3]: https://github.com/Z3Prover/z3
