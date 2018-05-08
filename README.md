minsynth
========

Install Z3 with its Python 3 bindings. With Homebrew:

    $ brew install z3 --with-python

Install our only Python dependency, [Lark][]:

    $ pip install --user lark-parser

Run a simple example to see how to synthesize values, which is stolen from [Aws Albarghouthi][aws]'s [primer][]:

    $ python3 ex1.py

Run a more complete synthesis engine for a little arithmetic language:

    $ python3 ex2.py < sketches/s1.txt

[lark]: https://github.com/lark-parser/lark
[primer]: http://barghouthi.github.io/2017/04/24/synthesis-primer/
[aws]: http://www.cs.wisc.edu/~aws
