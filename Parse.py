import ast
import unittest
import sys
import _ast

methods_by_spec = {}


class ModuleTransformer(ast.NodeTransformer):
    def visit_Module(self, module_node):
        module_node.body.insert(0, _ast.Import(
            names=[_ast.alias(name='unittest')]
        ))
        return module_node


class TestMethodTransformer(ast.NodeVisitor):
    def __init__(self, class_name) -> None:
        super().__init__()
        self.class_name = class_name

    def visit_FunctionDef(self, function_node):
        if not function_node.name.startswith('_'):
            if self.class_name in methods_by_spec:
                methods_by_spec[self.class_name].append(function_node.name)
            else:
                methods_by_spec[self.class_name] = [function_node.name]


class ComparatorTransformer(ast.NodeTransformer):
    def visit_Expr(self, expression_node):
        expression_value = expression_node.value
        if type(expression_value) is _ast.Compare:
            comparison_method = 'assertEquals'

            expression_node.value = _ast.Call(
                func=_ast.Attribute(
                    value=_ast.Name(id='self', ctx=_ast.Load()),
                    attr=comparison_method,
                    ctx=_ast.Load()
                ),
                args=[expression_value.left, expression_value.comparators[0]],
                keywords=[]
            )
            return expression_node


class SpecTransformer(ast.NodeTransformer):
    def visit_ClassDef(self, class_node):
        if class_node.name.endswith('Spec'):
            class_node.bases.append(_ast.Attribute(
                value=_ast.Name(id='unittest', ctx=_ast.Load()),
                attr='TestCase',
                ctx=_ast.Load()
            ))

            TestMethodTransformer(class_node.name).visit(class_node)
            ComparatorTransformer().visit(class_node)

        return class_node


with open('examples/TestA.py', 'r') as f:
    text = f.read()
    node = ast.parse(text, mode='exec')
    ModuleTransformer().visit(node)
    SpecTransformer().visit(node)
    ast.fix_missing_locations(node)
    compiled = compile(node, 'TestA.py', mode='exec')
    exec(compiled)

suite = unittest.TestSuite()

this_module = sys.modules[__name__]

for spec_class in methods_by_spec:
    spec_class_impl = getattr(this_module, spec_class)

    spec_methods = methods_by_spec[spec_class]
    for spec_method in spec_methods:
        suite.addTest(spec_class_impl(spec_method))

unittest.TextTestRunner(verbosity=2).run(suite)
