# import statements
from brewparse import parse_program
from intbase import InterpreterBase, ErrorType
from element import Element


class Interpreter(InterpreterBase):
    # Constructor built using InterpreterBase as inherited from intbase
    # console_output parameter indicates where an interpreted program’s output should be directed
    # inp parameter is used for testing scripts.
    # trace_output parameter is used to help in debugging. Set to true if you want to be able to use python print
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
    
    # run function
    def run(self, program):
        # create the Abstract Syntax Tree from provided string program
        ast =  parse_program(program)
        
        # map for holding all variables | key: variable name; val: value of variable
        self.variable_name_to_val = {}

        # currently ast holds the program node. We will now run all function nodes enclosed in this program
        func_count = len(ast.get("functions"))

        # First, we want to ensure we actually have the main function
        main_flag = False
        for i in range(func_count):
           if ast.get("functions")[i].get("name") == "main":
               main_flag = True
               break

        # ERROR: NO MAIN FUNCTION
        if not main_flag:
            super().error(
                ErrorType.NAME_ERROR,
                "No main() function was found",
            )
        
        ### WILL NEED IMPROVEMENT ###
        # run all the functions
        for i in range(func_count):
           self.run_func(ast.get("functions")[i])


    # run the different functions nodes under the program node (includes main)
    def run_func(self, function_node):
        # get the arguments of the function (will be unused for now)
        args = function_node.get("args") + []

        # find the number of statements enclosed in this function
        st_count = len(function_node.get("statements"))

        for i in range(st_count):
            self.execute_statement(function_node.get("statements")[i])


    # handles execution of each statement in the function
    def execute_statement(self, statement_node):
        # call execute_expression_equal if we see an "="
        if statement_node.elem_type == "=":
            self.execute_expression_equal(statement_node)
        # call execute_expression_function if we see a "fcall"
        elif statement_node.elem_type == "fcall":
            self.execute_expression_function(statement_node)

    
    # execute all binary operation related statements
    def execute_expression_equal(self, equal_node):
        # Extract the expression node from statement node
        expression_node = equal_node.get("expression")
        # Extract the name of variable from statement
        var_name = equal_node.get("name")

        # now we need to check what type of call comes next: either we are doing an operation, an assignment, or a function call
        # OPERATION:
        if (self.type_of_call(expression_node.elem_type) == "operation"):
            ans = self.evaluate_operations(expression_node)
            self.variable_name_to_val[var_name] = ans
            
        # ASSIGNMENT
        elif (self.type_of_call(expression_node.elem_type) == "assignment"):
            self.variable_name_to_val[var_name] = expression_node.get("val")

        # VARIABLE TO VARIABLE ASSIGNMENT
        elif (self.type_of_call(expression_node.elem_type) == "var_assign"):
            self.variable_name_to_val[var_name] = self.variable_value(expression_node, False)

        # FUNCTION CALL
        elif (self.type_of_call(expression_node.elem_type) == "function"):
            self.variable_name_to_val[var_name] = self.execute_expression_function(expression_node)

        # NEGATION
        elif (self.type_of_call(expression_node.elem_type) == "negative"):
            self.variable_name_to_val[var_name] = self.negation(expression_node)
        
        # UNEXPECTED ERROR
        elif (self.type_of_call(expression_node.elem_type) == "ERROR"):
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"An Unknown Call was made",
                )
        
        return 1

        
    # execute all function call related statements
    def execute_expression_function(self, function_node):
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
        
        # print function call
        elif func_name == "print":
            args_size = len(args)
            final_string = ""

            for arg in range(args_size):
                if self.type_of_call(args[arg].elem_type) == "assignment":
                    final_string += str(args[arg].get("val"))
                elif self.type_of_call(args[arg].elem_type) == "operation":
                    final_string += str(self.evaluate_operations(args[arg]))
                elif self.type_of_call(args[arg].elem_type) == "function":
                    final_string += str(self.execute_expression_function(args[arg]))
                elif args[arg].elem_type == "var":
                    final_string += str(self.variable_value(args[arg], False))
                elif args[arg].elem_type == "neg":
                    final_string += str(0 - self.evaluate_operations(args[arg].get("op1")))
            
            super().output(final_string)
        
        else:
            super().error(
                    ErrorType.NAME_ERROR,
                    f"Unknown Function Referenced",
                )

    # helper function that checks the type of call made by an expression
    def type_of_call(self, call):
        if call == "+" or call == "-":
            return "operation"
        elif call == "int" or call == "string":
            return "assignment"
        elif call == "fcall":
            return "function"
        elif call == "neg":
            return "negative"
        elif call == "var":
            return "var_assign"
        else:
            return "ERROR"

    # helper function that is able to evaluate any + & - expression given with int, var, and even a function
    def evaluate_operations(self, exp):

        # NEGATION EXPRESSION
        if exp.elem_type == "neg":
            return self.negation(exp)
        
        # FUNCTION CALL
        if exp.elem_type == "fcall":
            return self.execute_expression_function(exp)
        
        # INTEGER
        if exp.elem_type == "int":
            return exp.get("val")
        
        # VARIABLE
        if exp.elem_type == "var":
            return self.variable_value(exp, True)
        # STRING (THROW ERROR)
        if exp.elem_type == "string":
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for arithmetic operation",
            )
        
        # ELSE EXPRESSION STILL LEFT
        if exp.elem_type == "+":
            return self.evaluate_operations(exp.get("op1")) + self.evaluate_operations(exp.get("op2"))
        else:
            return self.evaluate_operations(exp.get("op1")) - self.evaluate_operations(exp.get("op2"))
    

    # returns value of inputted key for variable. Reduces need to error check everywhere and returns the value cleanly
    def variable_value(self, name, not_string):
        if name.get("name") not in self.variable_name_to_val:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {name.get('name')} has not been defined",
                )
        if not_string == True:
            if str(type(self.variable_name_to_val[name.get("name")])).split("'")[1] == "str":
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible types for arithmetic operation",
                )
        return self.variable_name_to_val[name.get("name")]
    
    # negation function takes care of both cases where we have an expression that is negated and a value that is negated
    def negation(self, neg_exp):
        if neg_exp.get("op1").elem_type == "int":
            return 0 - neg_exp.get("op1").get("val")
        elif neg_exp.get("op1").elem_type == "var":
            return 0 - self.variable_value(neg_exp.get("op1"), True)
        elif neg_exp.get("op1").get("val") is None:
                    ans = self.evaluate_operations(neg_exp.get("op1"))
                    return 0 - ans
            
# FOR TESTING PURPOSES
def main():
   program = """func main() {
               hello = "jslkf";
               a = 'hello';
               print(a);
               a = 3 - (-3 + (2 + inputi("Try negation: ")));
               b = "foo";
               print(-a);
               x = (5 + (6 + 2)) + (3 + 8);
               y = x - 9;
               u = 6 + y;
               z = 8;
               w = inputi("input pls work lol: ");
               v = "hello bruh";
               q = w + (y - z);
               print(print("hello"));
               v = 89;
               print(v);
               a = 4;
               a = -v;
               print(a);
               i = 2;
               i = ((5 + (6 - 3)) - ((i - 3) - (1 - 7))); 
               print(i);
           }
           """
   interpreter = Interpreter()
   interpreter.run(program)

if __name__ == "__main__":
   main()