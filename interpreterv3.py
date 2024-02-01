import copy
from enum import Enum

from brewparse import parse_program
from env_v3 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev3 import Type, Value, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        main_func = self.__get_func_by_name("main", 0)
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        ### LAMBDA ADDITION
        self.lambda_name_to_env = {}
        self.lambda_push = False

        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        if name in self.func_name_to_ast:
            candidate_funcs = self.func_name_to_ast[name]
        elif self.env.get(name) is not None:
            ### IF IT IS LAMBDA, PUSH ONTO ENVIRONMENT THE LAMBDA ENV AND TOGGLE LAMBDA_PUSH TO TRUE
            if not (self.env.get(name).type() == Type.FUNCTION or self.env.get(name).type() == Type.LAMBDA):
                super().error(ErrorType.TYPE_ERROR, f"{name} is not a callable function")
            if len(self.env.get(name).value().get("args")) != num_params:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {name} taking {num_params} params not found",
                )
            result = self.env.get(name).value()
            if self.env.get(name).type() == Type.LAMBDA:
                lda_env = self.lambda_name_to_env[self.env.get(name)]
                self.env.environment.append(lda_env)
                self.lambda_push = True
            return result
        else:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        if self.lambda_push == False:
            self.env.push()
        else:
            self.lambda_push = False
        for statement in statements:
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement)
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement)

            if status == ExecStatus.RETURN:
                self.env.pop()

                return (status, return_val)

        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_func(self, call_node):
        #print("THIS IS A CALL NODE: ")
        #print(call_node.__str__())
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        if func_name == "inputs":
            return self.__call_input(call_node)

        actual_args = call_node.get("args")
        func_ast = self.__get_func_by_name(func_name, len(actual_args))

        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )
        self.env.push()
        
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            # print(formal_ast)
            if actual_ast.elem_type == "lambda":
                lambda_env = self.env.create_lambda_env()
                if formal_ast.elem_type == "arg":
                    result = Value(Type.LAMBDA, actual_ast, 0)
                    self.lambda_name_to_env[result] = lambda_env
                elif formal_ast.elem_type == "refarg":
                    result = Value(Type.LAMBDA, actual_ast, 1)
                    self.lambda_name_to_env[result] = lambda_env
            elif formal_ast.elem_type == "refarg" and actual_ast.elem_type == "var":   
                result = self.env.get(actual_ast.get("name"))
                result.r = 1
            else:
                result = self.__eval_expr(actual_ast)
                if result.type() != Type.LAMBDA:
                    result = copy.deepcopy(result)
                
            arg_name = formal_ast.get("name")
            self.env.create(arg_name, result)
        # print("------------------")
        # print(func_ast)
        # print("+++++++++++++++++++")
        # print(self.lambda_name_to_env)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop()
        return return_val

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + str(get_printable(result))
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        # print("here expr")
        # print("type: " + str(expr_ast.elem_type))
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            # print("getting as nil")
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            # print("getting as str")
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val is None:
                if var_name not in self.func_name_to_ast:
                    super().error(ErrorType.NAME_ERROR, f"Variable/Function {var_name} not found")
                else:
                    val = self.func_name_to_ast[var_name]
                    args = val.keys()
                    args_list = list(args)
                    if len(args_list) > 1:
                        super().error(
                            ErrorType.NAME_ERROR,
                            f"Ambiguous Function call for {var_name}",
                        )
                    val = Value(Type.FUNCTION, val[args_list[0]])
            if val.type() == Type.LAMBDA:
                lambda_env = self.lambda_name_to_env[val]
                if val.is_ref() != 1:
                    val = Value(Type.LAMBDA, val.value(), 0)
                    self.lambda_name_to_env[val] = copy.deepcopy(lambda_env)
                else:
                    self.lambda_name_to_env[val] = lambda_env

            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            #_, ret_val = self.__call_func(expr_ast)
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        if expr_ast.elem_type == Interpreter.LAMBDA_DEF:
            val = Value(Type.LAMBDA, expr_ast, 0)
            lambda_env = self.env.create_lambda_env()
            self.lambda_name_to_env[val] = lambda_env
            return val

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        # Handles Coercion of integers to binary when using "==" or "!="
        if arith_ast.elem_type == "==" or arith_ast.elem_type == "!=" or arith_ast.elem_type == ">" or arith_ast.elem_type == ">="or arith_ast.elem_type == "<" or arith_ast.elem_type == "<=" or arith_ast.elem_type == "&&" or arith_ast.elem_type == "||":
            if left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL:
                left_value_obj = Value(Type.BOOL, self.__int_to_bin_coercion(left_value_obj.value()))
            elif right_value_obj.type() == Type.INT and left_value_obj.type() == Type.BOOL:
                right_value_obj = Value(Type.BOOL, self.__int_to_bin_coercion(right_value_obj.value()))
        
        # Handles Coercion of binary to integers when using "+", "-", "/", "*"
        if arith_ast.elem_type == "+" or arith_ast.elem_type == "-" or arith_ast.elem_type == "*" or arith_ast.elem_type == "/":
            if left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT:
                left_value_obj = Value(Type.INT, self.__bin_to_int_coercion(left_value_obj.value()))
            elif right_value_obj.type() == Type.BOOL and left_value_obj.type() == Type.INT:
                right_value_obj = Value(Type.INT, self.__bin_to_int_coercion(right_value_obj.value()))
        
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        # print("here eval")
        # print(arith_ast)
        # print("evaluating " + str(left_value_obj.type()) + " " + str(arith_ast.elem_type))
        # print("obj left: " + str(left_value_obj.value()))
        return f(left_value_obj, right_value_obj)

    def __int_to_bin_coercion(self, value):
        if value != 0:
            return True
        else:
            return False
        
    def __bin_to_int_coercion(self, value):
        if value == True:
            return 1
        else:
            return 0

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() != t and value_obj.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        
        #if an integer is passed in for "!" operator, use its value to compute the corresponding True/False value
        v = value_obj.value()
        if t == Type.BOOL and value_obj.type() == Type.INT:
            v = self.__int_to_bin_coercion(v)
        return Value(t, f(v))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["&&"] = lambda x, y: Value(
            Type.BOOL, self.__int_to_bin_coercion(x.value()) and self.__int_to_bin_coercion(y.value())
        )
        self.op_to_lambda[Type.INT]["||"] = lambda x, y: Value(
            Type.BOOL, self.__int_to_bin_coercion(x.value()) or self.__int_to_bin_coercion(y.value())
        )

        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.BOOL]["+"] = lambda x, y: Value(
            Type.INT, self.__bin_to_int_coercion(x.value()) + self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL]["-"] = lambda x, y: Value(
            Type.INT, self.__bin_to_int_coercion(x.value()) - self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL]["*"] = lambda x, y: Value(
            Type.INT, self.__bin_to_int_coercion(x.value()) * self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL]["/"] = lambda x, y: Value(
            Type.INT, self.__bin_to_int_coercion(x.value()) // self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL][">"] = lambda x, y: Value(
            Type.BOOL, self.__bin_to_int_coercion(x.value()) > self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL][">="] = lambda x, y: Value(
            Type.BOOL, self.__bin_to_int_coercion(x.value()) >= self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL]["<"] = lambda x, y: Value(
            Type.BOOL, self.__bin_to_int_coercion(x.value()) < self.__bin_to_int_coercion(y.value())
        )
        self.op_to_lambda[Type.BOOL]["<="] = lambda x, y: Value(
            Type.BOOL, self.__bin_to_int_coercion(x.value()) <= self.__bin_to_int_coercion(y.value())
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on function
        self.op_to_lambda[Type.FUNCTION] = {}
        self.op_to_lambda[Type.FUNCTION]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.FUNCTION]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on Lambda
        self.op_to_lambda[Type.LAMBDA] = {}
        self.op_to_lambda[Type.LAMBDA]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.LAMBDA]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if not(result.type() == Type.BOOL or result.type() == Type.INT):
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast)
            if not (run_while.type() == Type.BOOL or run_while.type() == Type.INT):
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for while condition",
                )
            if run_while.value():
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = self.__eval_expr(expr_ast)
        if value_obj.type() == Type.LAMBDA:
            if value_obj in self.lambda_name_to_env:
                lambda_env = copy.deepcopy(self.lambda_name_to_env[value_obj])
                value_obj = copy.deepcopy(value_obj)
                self.lambda_name_to_env[value_obj] = lambda_env
                return (ExecStatus.RETURN, value_obj)
            else:
                lambda_en = self.env.create_lambda_env()
                value_obj = copy.deepcopy(value_obj)
                self.lambda_name_to_env[value_obj] = lambda_en
                return (ExecStatus.RETURN, value_obj)
        value_obj = copy.deepcopy(value_obj)
        return (ExecStatus.RETURN, value_obj)
    

# FOR TESTING PURPOSES
def main():
    program = """
            func foo() { 
                print("yello");
                y = 20;
            }

            func main() {
                x = 10;
                print("YER MADE IT HERE MAYTEY");
                afoo = foo;
                print("Aint no fuckin way dawg");
            }
            """
    interpreter = Interpreter()
    interpreter.run(program)

if __name__ == "__main__":
    main()