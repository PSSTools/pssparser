
import os
import urllib.request
import urllib.parse
import subprocess
import shutil

def find_jre_windows():
    import winreg
    
    java_key_paths = (
        'SOFTWARE\\JavaSoft\\JRE',
        'SOFTWARE\\JavaSoft\\Java Runtime Environment',
        'SOFTWARE\\JavaSoft\\JDK'
    )
            
    for java_key_path in java_key_paths:
        looking_for = java_key_path
        try:
            kjava = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, java_key_path,
                                access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            looking_for = java_key_path + "\\CurrentVersion"
            kjava_values = dict([winreg.EnumValue(kjava, i)[:2]
                                for i in range(winreg.QueryInfoKey(kjava)[1])])
            current_version = kjava_values['CurrentVersion']
            looking_for = java_key_path + '\\' + current_version
            kjava_current = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, looking_for,
                                        access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            kjava_current_values = dict([winreg.EnumValue(kjava_current, i)[:2]
                                        for i in range(winreg.QueryInfoKey(kjava_current)[1])])
            return os.path.join(kjava_current_values['JavaHome'], "bin", "java")
        except WindowsError as e:
            if e.errno == 2:
                continue
            else:
                raise
            

scripts_dir=os.path.dirname(os.path.realpath(__file__))
root_dir=os.path.dirname(scripts_dir)

antlr_jar_name="antlr-4.8-complete.jar"
antlr_jar_url="https://www.antlr.org/download/" + antlr_jar_name

antlr_jar=os.path.join(scripts_dir, antlr_jar_name)

if not os.path.isfile(antlr_jar):
    raise Exception("Missing ANTLR jar")

jre = find_jre_windows()

pssparser_gen = os.path.join(root_dir, "gen-src", "pssparser_gen")
grammar = os.path.join(root_dir, "gen-src", "grammar")

if not os.path.isdir(grammar):
    os.mkdir(grammar)

cmd = [jre, "-jar", antlr_jar, "-Dlanguage=Python3", "-visitor"]
cmd.append(os.path.join(root_dir, "grammar", "PSS.g4"))
cmd.append("-o")
cmd.append(os.path.join(root_dir, "gen-src", "grammar"))

subprocess.call(cmd)

# Ensure the __init__.py file exists

with open(os.path.join(pssparser_gen, "__init__.py"), "w"):
    pass

for f in os.listdir(grammar):
    shutil.copy(
        os.path.join(grammar, f), 
        os.path.join(pssparser_gen, f))

shutil.rmtree(grammar)

# TODO: cleanup

