import lark
import z3
import sys

# A language based on a Lark example from:
# https://github.com/lark-parser/lark/wiki/Examples
GRAMMAR = """
?start: sum
  | sum "?" sum ":" sum -> if

?sum: term
  | sum "+" term        -> add
  | sum "-" term        -> sub

?term: item
  | term "*"  item      -> mul
  | term "/"  item      -> div
  | term ">>" item      -> shr
  | term "<<" item      -> shl

?item: INT              -> int
  | FLOAT               -> float
  | "-" item            -> neg
  | "int" item          -> intcast
  | "float" item        -> floatcast
  | "int2bv" item       -> int2bv
  | "float2bv" item     -> float2bv
  | CNAME               -> var
  | "(" start ")"

%import common.NUMBER
%import common.INT
%import common.FLOAT
%import common.WS
%import common.CNAME
%ignore WS
""".strip()


def interp(tree, lookup, z3_mode):
    """Evaluate the arithmetic expression.

    Pass a tree as a Lark `Tree` object for the parsed expression. For
    `lookup`, provide a function for mapping variable names to values.
    """

    op = tree.data
    if op in ('add', 'sub', 'mul', 'div', 'shl', 'shr'):  # Binary operators.
        lhs = interp(tree.children[0], lookup, z3_mode)
        rhs = interp(tree.children[1], lookup, z3_mode)
        if op == 'add':
            return lhs + rhs
        elif op == 'sub':
            return lhs - rhs
        elif op == 'mul':
            return lhs * rhs
        elif op == 'div':
            return lhs / rhs
        elif op == 'shl':
            return lhs << rhs
        elif op == 'shr':
            return lhs >> rhs
    elif op == 'neg':  # Negation.
        sub = interp(tree.children[0], lookup, z3_mode)
        return -sub
    elif op == 'int':  # Literal number.
        if z3_mode:
            return z3.BitVecVal(int(tree.children[0]), 32)
        else:
            return int(tree.children[0])
    elif op == 'float':  # Literal number.
        if z3_mode:
            return z3.BitVecVal(float(tree.children[0]), 32)
        else:
            return float(tree.children[0])
    elif op == 'var':  # Variable lookup.
        return lookup(tree.children[0])
    elif op == 'if':  # Conditional.
        cond = interp(tree.children[0], lookup, z3_mode)
        true = interp(tree.children[1], lookup, z3_mode)
        false = interp(tree.children[2], lookup, z3_mode)
        return (cond != 0) * true + (cond == 0) * false
    elif op == "intcast":
        child = interp(tree.children[0], lookup, z3_mode)
        if z3_mode:
            return z3.BV2Int(child)
        else:
            return int(child)
    elif op == "floatcast":
        child = interp(tree.children[0], lookup, z3_mode)
        if z3_mode:
            return z3.fpBVToFP(child, z3.Float32())
        else:
            return float(child)
    elif op == "int2bv":
        child = interp(tree.children[0], lookup, z3_mode)
        if z3_mode:
            return z3.Int2BV(child, 32)
        else:
            return child
    elif op == "float2bv":
        child = interp(tree.children[0], lookup, z3_mode)
        if z3_mode:
            return z3.fpToIEEEBV(child)
        else:
            return child


def pretty(tree, subst={}, paren=False):
    """Pretty-print a tree, with optional substitutions applied.

    If `paren` is true, then loose-binding expressions are
    parenthesized. We simplify boolean expressions "on the fly."
    """

    # Add parentheses?
    if paren:
        def par(s):
            return '({})'.format(s)
    else:
        def par(s):
            return s

    op = tree.data
    if op in ('add', 'sub', 'mul', 'div', 'shl', 'shr'):
        lhs = pretty(tree.children[0], subst, True)
        rhs = pretty(tree.children[1], subst, True)
        c = {
            'add': '+',
            'sub': '-',
            'mul': '*',
            'div': '/',
            'shl': '<<',
            'shr': '>>',
        }[op]
        return par('{} {} {}'.format(lhs, c, rhs))
    elif op == 'neg':
        sub = pretty(tree.children[0], subst)
        return '-{}'.format(sub, True)
    elif op == 'int' or op == 'float':
        return tree.children[0]
    elif op == 'var':
        name = tree.children[0]
        return str(subst.get(name, name))
    elif op == 'if':
        cond = pretty(tree.children[0], subst)
        true = pretty(tree.children[1], subst)
        false = pretty(tree.children[2], subst)
        return par('{} ? {} : {}'.format(cond, true, false))
    elif op == 'floatcast' or op=='intcast' or op=='float2bv' or op=='int2bv':
        return pretty(tree.children[0], subst, True)


def run(tree, env):
    """Ordinary expression evaluation.

    `env` is a mapping from variable names to values.
    """

    print(tree)
    return interp(tree, lambda n: env[n], False)


def z3_expr(tree, vars=None):
    """Create a Z3 expression from a tree.

    Return the Z3 expression and a dict mapping variable names to all
    free variables occurring in the expression. All variables are
    represented as BitVecs of width 8. Optionally, `vars` can be an
    initial set of variables.
    """

    vars = dict(vars) if vars else {}

    # Lazily construct a mapping from names to variables.
    def get_var(name):
        if name in vars:
            return vars[name]
        else:
            # v = z3.BitVec(name, 8)
            v = z3.BitVec(name, 32)
            vars[name] = v
            return v

    return interp(tree, get_var, True), vars


def solve(phi):
    """Solve a Z3 expression, returning the model.
    """

    s = z3.Solver()
    s.add(phi)
    s.check()
    return s.model()


def model_values(model):
    """Get the values out of a Z3 model.
    """
    return {
        d.name(): model[d]
        for d in model.decls()
    }

# https://stackoverflow.com/questions/22547988/how-to-calculate-absolute-value-in-z3-or-z3py
def abs(x):
    return z3.If(x >= 0,x,-x)


def synthesize(tree1, tree2):
    """Given two programs, synthesize the values for holes that make
    them equal.

    `tree1` has no holes. In `tree2`, every variable beginning with the
    letter "h" is considered a hole.
    """

    expr1, vars1 = z3_expr(tree1)
    expr2, vars2 = z3_expr(tree2, vars1)

    # Filter out the variables starting with "h" to get the non-hole
    # variables.
    plain_vars = {k: v for k, v in vars1.items()
                  if not k.startswith('h')}

    # Formulate the constraint for Z3.
    goal = z3.ForAll(
        list(plain_vars.values()),  # For every valuation of variables...
        # expr1 == expr2,  # ...the two expressions produce equal results.
        abs(expr1 - expr2) <= 10,
    )

    # Solve the constraint.
    return solve(goal)


def ex2(source):
    src1, src2 = source.strip().split('\n')

    parser = lark.Lark(GRAMMAR)
    tree1 = parser.parse(src1)
    tree2 = parser.parse(src2)

    model = synthesize(tree1, tree2)
    print(pretty(tree1))
    print(pretty(tree2, model_values(model)))

    # print(run(tree2, {'a': 3.0, 'h1': 15, 'h2': 1}))

if __name__ == '__main__':
    ex2(sys.stdin.read())
