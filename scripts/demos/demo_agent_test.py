"""Demo file to test agents with intentional issues."""


def bad_spacing(x, y, z):
    result = x + y + z
    return result


def unused_variable_test():
    x = 1
    y = 2
    unused = 999
    return x + y


class BadlyFormattedClass:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name
