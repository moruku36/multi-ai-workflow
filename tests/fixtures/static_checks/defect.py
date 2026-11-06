import subprocess


def unsafe(command, expression):
    subprocess.run(command, shell=True)
    value = eval(expression)
    try:
        return missing_name + value
    except Exception:
        pass
