# import statements
from brewparse import parse_program
from intbase import InterpreterBase, ErrorType
from element import Element
import copy


class Interpreter(InterpreterBase):

    NIL_VALUE = None

    # Constructor built using InterpreterBase as inherited from intbase
    # console_output parameter indicates where an interpreted program’s output should be directed
    # inp parameter is used for testing scripts.
    # trace_output parameter is used to help in debugging. Set to true if you want to be able to use python print
    def __init__(self, console_output=True, inp=None, trace_output=True):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        self.trace_output = trace_output
    
    # run function
    def run(self, program):
        # create the Abstract Syntax Tree from provided string program
        ast =  parse_program(program)

        # map for holding all functions | key: (function name, arg num); val: (arguments, statements)
        self.functions= {}

        # stack to hold function frames which will include if and while loops to preserve dynamic scoping restrictions | (function name, arg num)
        self.func_stack = []

        # Return flag
        self.return_flag = False

        # number of ifs
        self.ifnums = 0

        # number of whiles
        self.whilenums = 0

        self.rec_func_calls = 1

        # currently ast holds the program node. We will now run all function nodes enclosed in this program
        func_count = len(ast.get("functions"))

        # First, we want to ensure we actually have the main function
        main_flag = False
        for i in range(func_count):
           # map for holding all variables | key: variable name; val: value of variable
           variable_name_to_val = {}
           func_name = ast.get("functions")[i].get("name")
           arg_num = len(ast.get("functions")[i].get("args"))
           arguments = ast.get("functions")[i].get("args")
           statements = ast.get("functions")[i].get("statements")

           self.functions[(func_name, arg_num)] = [arguments, statements, variable_name_to_val]
           if self.trace_output == True:
               print(ast.get("functions")[i].__str__())
           if ast.get("functions")[i].get("name") == "main":
               main_flag = True
        
        # self.functions[('foo', 1)][2]['a'] = 67
        if self.trace_output:
            print(self.functions)
        # ERROR: NO MAIN FUNCTION
        if not main_flag:
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )
        
        ### WILL NEED IMPROVEMENT ###
        # run all the functions
        for i in range(func_count):
            if ast.get("functions")[i].get("name") == "main":
                self.func_stack.append(('main', 0))
                self.run_func(ast.get("functions")[i], 'main', 0, [], 'main', 0)


    # run the different functions nodes under the program node (includes main)
    def run_func(self, function_node, callee_func_name, callee_arg_num, caller_args, caller_func_name, caller_arg_num):
        # get the arguments of the function (will be unused for now)
        if self.trace_output:
            print("function_node:\t" + function_node.__str__())
            print("callee_func_name\t" + callee_func_name)
            print("callee_arg_num\t" + str(callee_arg_num))
            if len(caller_args) > 0:
                for ar in caller_args:
                    print(ar)
            print("caller_func_name\t" + caller_func_name)
            print("caller_arg_num\t" + str(caller_arg_num))

        callee_args = self.functions[(callee_func_name, callee_arg_num)][0]
        passed_args = []
        for arg in caller_args:
            call = self.type_of_call(arg.elem_type)
            if call == "operation":
                ans = self.evaluate_boolean_operations(arg, caller_func_name, caller_arg_num)
            
            elif call == "assignment":
                ans = arg.get("val")

            elif call == "var_assign":
                ans = self.variable_value(arg, False, False, True, caller_func_name, caller_arg_num)

            elif call == "function":
                ans = self.execute_expression_function(arg, caller_func_name, caller_arg_num)

            elif call == "negative":
                ans = (0 - self.evaluate_operations(arg.get("op1"), caller_func_name, caller_arg_num))

            elif call == "nil_assign":
                ans = None

            elif call == "not_op":
                ans = (not self.evaluate_boolean_operations(arg.get("op1"), caller_func_name, caller_arg_num))
                
            elif call == "ERROR":
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Unknown Argument Type/Operation/Function",
                )

            passed_args.append(ans)
        for i in range(callee_arg_num):
            self.functions[(callee_func_name, callee_arg_num)][2][callee_args[i].get("name")] = passed_args[i]

        # find the number of statements enclosed in this function
        st_count = len(self.functions[(callee_func_name, callee_arg_num)][1])
        ret = None
        for i in range(st_count):
            ret = self.execute_statement(self.functions[(callee_func_name, callee_arg_num)][1][i], callee_func_name, callee_arg_num)
            if self.return_flag:
                self.return_flag = False;
                return ret
        return ret


    # handles execution of each statement in the function
    def execute_statement(self, statement_node, func_name, arg_num):
        # call execute_expression_equal if we see an "="
        ##### TESTER PRINT STMT #####
        if (self.trace_output):
            print(statement_node.__str__())
        if statement_node.elem_type == "=":
            self.execute_expression_equal(statement_node, func_name, arg_num)
        # call execute_expression_function if we see a "fcall"
        elif statement_node.elem_type == InterpreterBase.FCALL_DEF:
            retf = self.execute_expression_function(statement_node, func_name, arg_num)
            if self.return_flag:
                return retf
        elif statement_node.elem_type == InterpreterBase.IF_DEF:
            retf = self.execute_if_expression(statement_node, func_name, arg_num)
            if self.return_flag:
                return retf
        elif statement_node.elem_type == InterpreterBase.WHILE_DEF:
            retf = self.execute_while_expression(statement_node, func_name, arg_num)
            if self.return_flag:
                return retf
        elif statement_node.elem_type == InterpreterBase.RETURN_DEF:
            # print(statement_node.get("expression"))
            if statement_node.get("expression") is None:
                self.return_flag = True
                return None
            call = self.type_of_call(statement_node.get("expression").elem_type)
            if call == "operation":
                ans = self.evaluate_boolean_operations(statement_node.get("expression"), func_name, arg_num)
        
            elif call == "assignment":
                ans = statement_node.get("expression").get("val")

            elif call == "var_assign":
                ans = self.variable_value(statement_node.get("expression"), False, False, True, func_name, arg_num)

            elif call == "function":
                ans = self.execute_expression_function(statement_node.get("expression"),func_name, arg_num)

            elif call == "negative":
                ans = (0 - self.evaluate_operations(statement_node.get("expression").get("op1"), func_name, arg_num))

            elif call == "nil_assign":
                ans = None

            elif call == "not_op":
                ans = (not self.evaluate_boolean_operations(statement_node.get("expression").get("op1"), func_name, arg_num))
                
            elif call == "ERROR":
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Unknown Argument Type/Operation/Function",
                )
            self.return_flag = True
            return ans

    
    # execute all binary operation related statements
    def execute_expression_equal(self, equal_node, func_name, arg_num):
        # Extract the expression node from statement node
        expression_node = equal_node.get("expression")
        # Extract the name of variable from statement
        var_name = equal_node.get("name")

        func = (func_name, arg_num)
        for function in reversed(self.func_stack):
            if var_name in self.functions[function][2]:
                func = function
                break
        # now we need to check what type of call comes next: either we are doing an operation, an assignment, or a function call
        # OPERATION:
        if (self.type_of_call(expression_node.elem_type) == "operation"):
            # print(expression_node.get("op1").get("op2").__str__())
            ans = self.evaluate_boolean_operations(expression_node, func_name, arg_num)
            self.functions[func][2][var_name] = ans
            
        # ASSIGNMENT
        elif (self.type_of_call(expression_node.elem_type) == "assignment"):
            ans = expression_node.get("val")
            self.functions[func][2][var_name] = ans
            ##### TESTER PRINT STMT #####
            # if (self.trace_output):
            #     print(str(type(self.functions[(func_name, arg_num)][2][var_name])))

        # VARIABLE TO VARIABLE ASSIGNMENT
        elif (self.type_of_call(expression_node.elem_type) == "var_assign"):
            ans = self.variable_value(expression_node, False, False, False, func_name, arg_num)
            self.functions[func][2][var_name] = ans

        # NIL ASSIGNMENT
        elif (self.type_of_call(expression_node.elem_type) == "nil_assign"):
            ans = Interpreter.NIL_VALUE
            self.functions[func][2][var_name] = ans
            ##### TESTER PRINT STMT #####
            # if (self.trace_output):
            #     print(str(type(self.functions[(func_name, arg_num)][2][var_name])))

        # FUNCTION CALL
        elif (self.type_of_call(expression_node.elem_type) == "function"):
            ans = self.execute_expression_function(expression_node, func_name, arg_num)
            self.functions[func][2][var_name] = ans

        # NEGATION
        elif (self.type_of_call(expression_node.elem_type) == "negative"):
            ans = self.negation(expression_node, func_name, arg_num)
            self.functions[func][2][var_name] = ans

        # NOT OPERATION
        elif (self.type_of_call(expression_node.elem_type) == "not_op"):
            ans = self.not_operation(expression_node, func_name, arg_num)
            self.functions[func][2][var_name] = ans
        
        # UNEXPECTED ERROR
        elif (self.type_of_call(expression_node.elem_type) == "ERROR"):
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"An Unknown Call was made",
                )
        
        return 1

        
    # execute all function call related statements
    def execute_expression_function(self, function_node, fname, arg_num):
        # Extract the name of the function along with its arguments
        func_name = function_node.get("name")
        args = function_node.get("args")

        # inputi function call
        if func_name == "inputi":
            if not args:
                user_input = super().get_input()
                return int(user_input)
            elif len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputi() function found that takes > 1 parameter",
                )
                
            else:
                super().output(args[0].get("val"))
                user_input = super().get_input()
                return int(user_input)
        
        # inputs function call
        elif func_name == "inputs":
            if not args:
                user_input = super().get_input()
                return str(user_input)
            elif len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputs() function found that takes > 1 parameter",
                )
            else:
                super().output(args[0].get("val"))
                user_input = super().get_input()
                return str(user_input)
        
        # print function call
        elif func_name == "print":
            ##### TESTER PRINT STMT #####
            if (self.trace_output):
                print(self.functions[(fname, arg_num)][2])
            args_size = len(args)
            final_string = ""
          
            for arg in range(args_size):
                if self.type_of_call(args[arg].elem_type) == "assignment":
                    ans = args[arg].get("val")
                    if str(type(ans)).split("'")[1] == "bool":
                        if str(ans) == "True":
                            ans = "true"
                        elif str(ans) == "False":
                            ans = "false"
                    final_string += str(ans)

                elif self.type_of_call(args[arg].elem_type) == "operation":
                    ans = self.evaluate_boolean_operations(args[arg], fname, arg_num)
                    if str(type(ans)).split("'")[1] == "bool":
                        if str(ans) == "True":
                            ans = "true"
                        elif str(ans) == "False":
                            ans = "false"
                    final_string += str(ans)

                elif self.type_of_call(args[arg].elem_type) == "function":
                    ans = self.execute_expression_function(args[arg], fname, arg_num)
                    if str(type(ans)).split("'")[1] == "bool":
                        if str(ans) == "True":
                            ans = "true"
                        elif str(ans) == "False":
                            ans = "false"
                    final_string += str(ans)

                elif args[arg].elem_type == "var":
                    ans = self.variable_value(args[arg], False, False, True, fname, arg_num)
                    if str(type(ans)).split("'")[1] == "bool":
                        if str(ans) == "True":
                            ans = "true"
                        elif str(ans) == "False":
                            ans = "false"
                    final_string += str(ans)

                elif args[arg].elem_type == "neg":
                    final_string += str(0 - self.evaluate_operations(args[arg].get("op1"), fname, arg_num))

                elif args[arg].elem_type == "!":
                    ans = str(self.evaluate_boolean_operations(args[arg].get("op1"), fname, arg_num))
                    if ans == "True":
                        ans = "false"
                    elif ans == "False":
                        ans = "true"
                    final_string += ans
            
            ##### TESTER CODE #####
            if self.trace_output:
                print(self.functions)
            super().output(final_string)
            return None
        
        elif ((func_name, len(args)) in self.functions):
            if (function_node.get("name"), len(args)) in self.func_stack:
                self.func_stack.append((function_node.get("name") + str(self.rec_func_calls), len(args)))
                arguments = self.functions[(function_node.get("name"), len(args))][0]
                statements = self.functions[(function_node.get("name"), len(args))][1]
                self.functions[(function_node.get("name") + str(self.rec_func_calls), len(args))] = [arguments, statements, {}]
                self.rec_func_calls = self.rec_func_calls + 1
                ret = self.run_func(function_node, function_node.get("name") + str(self.rec_func_calls - 1), len(args), args, fname, arg_num)

                self.func_stack.pop()
                
            else:
                self.func_stack.append((function_node.get("name"), len(args)))
                ret = self.run_func(function_node, function_node.get("name"), len(args), args, fname, arg_num)
                self.func_stack.pop()
            return ret


        else:
            super().error(
                    ErrorType.NAME_ERROR,
                    f"Unknown Function Referenced",
                )
    
    def execute_if_expression(self, statement, func_name, arg_num):
        bool_exp = self.evaluate_boolean_operations(statement.get("condition"), func_name, arg_num)
        if str(type(bool_exp)).split("'")[1] != "bool":
            super().error(
                ErrorType.TYPE_ERROR,
                "The if condition passed in does not evaluate to boolean",
            )
        self.ifnums = self.ifnums + 1
        self.functions[('if', self.ifnums)] = [[], [], {}]
        self.func_stack.append(('if', self.ifnums))

        if bool_exp:
            for stmt in statement.get("statements"):
                ret = self.execute_statement(stmt, 'if', self.ifnums - 1)
                if self.return_flag:
                    self.func_stack.pop()
                    return ret
                
        elif statement.get("else_statements") is not None:
            for stmt in statement.get("else_statements"):
                ret = self.execute_statement(stmt, 'if', self.ifnums - 1)
                if self.return_flag:
                    self.func_stack.pop()
                    return ret
                
        self.func_stack.pop()

    def execute_while_expression(self, statement, func_name, arg_num):
        bool_exp = self.evaluate_boolean_operations(statement.get("condition"), func_name, arg_num)
        if str(type(bool_exp)).split("'")[1] != "bool":
            super().error(
                ErrorType.TYPE_ERROR,
                "The while condition passed in does not evaluate to boolean",
            )
        self.whilenums = self.whilenums + 1
        self.functions[('while', self.whilenums)] = [[], [], {}]
        self.func_stack.append(('while', self.whilenums))

        while(self.evaluate_boolean_operations(statement.get("condition"), 'while', self.whilenums - 1)):
            for stmt in statement.get("statements"):
                ret = self.execute_statement(stmt, 'while', self.whilenums - 1)
                if self.return_flag:
                    self.func_stack.pop()
                    return ret
                
        self.func_stack.pop()

    # helper function that checks the type of call made by an expression
    def type_of_call(self, call):
        if call == "+" or call == "-" or call == "*" or call == "/" or call == "&&" or call == "==" or call == "||" or call == ">" or call == "<" or call == ">=" or call == "<=" or call == "!=":
            return "operation"
        elif call == InterpreterBase.INT_DEF or call == InterpreterBase.STRING_DEF or call == InterpreterBase.BOOL_DEF:
            return "assignment"
        elif call == InterpreterBase.FCALL_DEF:
            return "function"
        elif call == InterpreterBase.NEG_DEF:
            return "negative"
        elif call == InterpreterBase.VAR_DEF:
            return "var_assign"
        elif call == InterpreterBase.NIL_DEF:
            return "nil_assign"
        elif call == InterpreterBase.NOT_DEF:
            return "not_op"
        else:
            return "ERROR"

    # helper function that is able to evaluate any +, -, /, * expression given with int, str, var, and even a function
    def evaluate_operations(self, exp, func_name, arg_num):

        # NEGATION EXPRESSION
        if exp.elem_type == InterpreterBase.NEG_DEF:
            return self.negation(exp, func_name, arg_num)
        
        # FUNCTION CALL
        if exp.elem_type == InterpreterBase.FCALL_DEF:
            
            ans = self.execute_expression_function(exp, func_name, arg_num)
            # print(str(ans))
            return ans
        
        # INTEGER
        if exp.elem_type == InterpreterBase.INT_DEF:
            return exp.get("val")
        
        # VARIABLE
        if exp.elem_type == InterpreterBase.VAR_DEF:
            return self.variable_value(exp, False, True, True, func_name, arg_num)  #CHANGE HERE
        
        # STRING
        if exp.elem_type == InterpreterBase.STRING_DEF:
            return exp.get("val")
        
        # BOOL OR NIL (THROW ERROR)
        if exp.elem_type == InterpreterBase.BOOL_DEF or exp.elem_type == InterpreterBase.NIL_DEF:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type '{exp.elem_type}' for arithmetic operation",
            )
        
        # Recursively solve the operations
        op1 = self.evaluate_operations(exp.get("op1"), func_name, arg_num)
        op2 = self.evaluate_operations(exp.get("op2"), func_name, arg_num)

        # If both operations are on different types, return error.
        if str(type(op1)).split("'")[1] != str(type(op2)).split("'")[1]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for arithmetic operation",
            )
        

        # Perform the designated operation
        if exp.elem_type == "*":
            if str(type(op1)).split("'")[1] == "str":
                super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for * operation",
            )
            return op1 * op2
        elif exp.elem_type == "/":
            if str(type(op1)).split("'")[1] == "str":
                super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for / operation",
            )
            return op1 // op2
        elif exp.elem_type == "+":
            ans = op1 + op2
            # print("ADD: " + str(ans))
            return ans
        elif exp.elem_type == "-":
            if str(type(op1)).split("'")[1] == "str":
                super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for - operation",
            )
            return op1 - op2

    def evaluate_boolean_operations(self, exp, func_name, arg_num):
        # NEGATION EXPRESSION
        if exp.elem_type == InterpreterBase.NEG_DEF:
            return self.negation(exp, func_name, arg_num)
        
        # NOT OPERATION
        if exp.elem_type == InterpreterBase.NOT_DEF:
            return self.not_operation(exp, func_name, arg_num)
        
        # FUNCTION CALL
        if exp.elem_type == InterpreterBase.FCALL_DEF:
            return self.execute_expression_function(exp, func_name, arg_num)
        
        # INTEGER
        if exp.elem_type == InterpreterBase.INT_DEF:
            return exp.get("val")
        
        # VARIABLE
        if exp.elem_type == InterpreterBase.VAR_DEF:
            return self.variable_value(exp, False, False, False, func_name, arg_num)  #CHANGE HERE
        
        # STRING
        if exp.elem_type == InterpreterBase.STRING_DEF:
            return exp.get("val")
        
        if exp.elem_type == InterpreterBase.BOOL_DEF:
            return exp.get("val")
        
        if exp.elem_type == InterpreterBase.NIL_DEF:
            return Interpreter.NIL_VALUE

        if exp.elem_type == "+" or exp.elem_type == "-" or exp.elem_type == "*" or exp.elem_type == "/":
            return self.evaluate_operations(exp, func_name, arg_num)

        op1 = self.evaluate_boolean_operations(exp.get("op1"), func_name, arg_num)
        op2 = self.evaluate_boolean_operations(exp.get("op2"), func_name, arg_num)

        # if str(type(op1)).split("'")[1] != str(type(op2)).split("'")[1]:
        #     super().error(
        #         ErrorType.TYPE_ERROR,
        #         f"Incompatible types for boolean operation",
        #     )

        if exp.elem_type == "==":
            if str(type(op1)).split("'")[1] != str(type(op2)).split("'")[1]:
                return False;
            if op1 == op2:
                return True
            else:
                return False
        
        if exp.elem_type == "!=":
            if str(type(op1)).split("'")[1] != str(type(op2)).split("'")[1]:
                return True;
            if op1 != op2:
                return True
            else:
                return False

        if exp.elem_type == "&&":
            if str(type(op1)).split("'")[1] != "bool" or str(type(op2)).split("'")[1] != "bool":
                super().error(
                ErrorType.TYPE_ERROR,
                "'&&' expression requires boolean arguments",
            )
            if op1 == True and op2 == True:
                return True
            else:
                return False
            
        if exp.elem_type == "||":
            if str(type(op1)).split("'")[1] != "bool" or str(type(op2)).split("'")[1] != "bool":
                super().error(
                ErrorType.TYPE_ERROR,
                "'||' expression requires boolean arguments",
            )
            
            if op1 == True or op2 == True:
                return True
            else:
                return False
        
        if exp.elem_type == ">":
            if str(type(op1)).split("'")[1] != "int" or str(type(op2)).split("'")[1] != "int":
                super().error(
                ErrorType.TYPE_ERROR,
                "Cannot perform '>' on non-int arguments",
            )
            if op1 > op2:
                return True
            else:
                return False

        if exp.elem_type == "<":
            if str(type(op1)).split("'")[1] != "int" or str(type(op2)).split("'")[1] != "int":
                super().error(
                ErrorType.TYPE_ERROR,
                "Cannot perform '<' on non-int arguments",
            )
            if op1 < op2:
                return True
            else:
                return False
            
        if exp.elem_type == ">=":
            if str(type(op1)).split("'")[1] != "int" or str(type(op2)).split("'")[1] != "int":
                super().error(
                ErrorType.TYPE_ERROR,
                "Cannot perform '>=' on non-int arguments",
            )
            if op1 >= op2:
                return True
            else:
                return False
            
        if exp.elem_type == "<=":
            if str(type(op1)).split("'")[1] != "int" or str(type(op2)).split("'")[1] != "int":
                super().error(
                ErrorType.TYPE_ERROR,
                "Cannot perform '<=' on non-int arguments",
            )
            if op1 <= op2:
                return True
            else:
                return False


    # returns value of inputted key for variable. Reduces need to error check everywhere and returns the value cleanly
    def variable_value(self, name, not_string, not_bool, not_nil, func_name, arg_num):
        # if self.variable_name_to_val[name.get("name")] == True:
        #     return "true"
        # elif self.variable_name_to_val[name.get("name")] == False:
        #     return "false" 
        for function in reversed(self.func_stack):
            if name.get("name") in self.functions[function][2]:
                if not_string == True:
                    if str(type(self.functions[function][2][name.get("name")])).split("'")[1] == "str":
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible type 'str' for operation",
                        )

                elif not_bool == True:
                    if str(type(self.functions[function][2][name.get("name")])).split("'")[1] == InterpreterBase.BOOL_DEF:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible type 'bool' for operation",
                        )
                
                elif not_nil == True:
                    if str(type(self.functions[function][2][name.get("name")])).split("'")[1] == "NoneType":
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Incompatible type 'nil' for operation",
                        )
                return self.functions[function][2][name.get("name")]

        super().error(
            ErrorType.NAME_ERROR,
            f"Variable {name.get('name')} has not been defined",
        )
    
    # negation function takes care of both cases where we have an expression that is negated and a value that is negated
    def negation(self, neg_exp, func_name, arg_num):
        if neg_exp.get("op1").elem_type == "int":
            return 0 - neg_exp.get("op1").get("val")
        elif neg_exp.get("op1").elem_type == "var":
            return 0 - self.variable_value(neg_exp.get("op1"), True, True, True, func_name, arg_num)
        elif neg_exp.get("op1").get("val") is None:
            ans = self.evaluate_operations(neg_exp.get("op1"), func_name, arg_num)
            return 0 - ans
        
    def not_operation(self, not_exp, func_name, arg_num):
        if not_exp.get("op1").elem_type == "int" or not_exp.get("op1") == "str" or not_exp.get("op1") == "nil":
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for '!' operation",
            )
        if not_exp.get("op1").elem_type == "bool":
            return not not_exp.get("op1").get("val")
        elif not_exp.get("op1").elem_type == "var":
            ans = self.variable_value(not_exp.get("op1"), True, True, False, func_name, arg_num)
            if str(type(ans)).split("'")[1] != 'bool':
                super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for '!' operation",
            )
            return not ans
        elif not_exp.get("op1").get("val") is None:
            ans = self.evaluate_boolean_operations(not_exp.get("op1"), func_name, arg_num)
            return not ans
            
# FOR TESTING PURPOSES
def main():
    program = """
            func alpha(a)
            {
                return a;
            }

            func foo(z, y) {
                z = z + y;
                return alpha;
            }
            func main() {
                x = foo;
                w = lambda(p) { print("I'm a lambda" + p); };
                w(5);
            }
            """
    interpreter = Interpreter()
    interpreter.run(program)

if __name__ == "__main__":
    main()