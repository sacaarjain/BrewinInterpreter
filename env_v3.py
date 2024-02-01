# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
import copy

class EnvironmentManager:
    def __init__(self):
        self.environment = [{}]

    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env:
                return env[symbol]

        return None

    def create_lambda_env(self):
        lambda_env = {}
        for env in self.environment:
            lambda_env.update({key: copy.deepcopy(value) for key, value in env.items()})
        # print(lambda_env)
        return lambda_env

    def set(self, symbol, value):
        for env in reversed(self.environment):
            if symbol in env:
                if env[symbol].r == 1:
                    env[symbol].t = value.t
                    env[symbol].v = value.v
                else:
                    env[symbol] = value
                return

        # symbol not found anywhere in the environment
        self.environment[-1][symbol] = value

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        self.environment[-1][symbol] = value

    # used when we enter a nested block to create a new environment for that block
    def push(self):
        self.environment.append({})  # [{}] -> [{}, {}]

    # used when we exit a nested block to discard the environment for that block
    def pop(self):
        self.environment.pop()