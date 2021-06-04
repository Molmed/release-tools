from subprocess import check_output

def run(cmd):
    return check_output(cmd.split(" ")).decode("utf-8")
