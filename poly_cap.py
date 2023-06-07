# import wave
# import time
import sys
import itertools
import subprocess
import os, json

class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen. From http://code.activestate.com/recipes/134892/"""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()
    def __call__(self):
        return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys, termios # import termios now or else you'll get the Unix version on the Mac
    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

def getKey():
    inkey = _Getch()
    import sys
    for i in range(sys.maxsize):
        k=inkey()
        if k != '':
            break
    return k

def repeat_or_continue(name):
    print("capturing ", name, " enter for next, space to skip, q to quit")
    k = getKey()
    if k == "\r":
        return True
    elif k == " ":
        return False
    elif k == "q":
        quit()

def get_number_input(to_print):
    while True:
        print(to_print)
        try:
            a = int(input())
            return a
        except ValueError:
            pass

training_wav = "v1_1_1.wav"
cab_ir_wav = "impulse.wav"
cab_sweep_wav = "sweep.wav"
output_wav = "test1.wav"
print("which audio interface mic input e.g: 1")
mic_input = input()
print("which audio interface load box input e.g: 3")
load_box_input = input()
print("which audio interface training output e.g: 1")
training_output = input()
while True:
    print("Capturing amp")
    print("capturing with mic else load box, type mic or 1 for mic")
    m = input().lower()
    mic_or_loadbox = m == "true" or m == "mic" or m == "1"
    if mic_or_loadbox:
        audio_input = mic_input
    else:
        audio_input = load_box_input

    print("Amp brand")
    amp_brand = input().lower()
    print("Amp model")
    amp_model = input().lower()
    print("Amp year")
    amp_year = input().lower()
    print("tags, seperated by commas eg: combo, guitar or head, bass")
    tags = input().lower()
    num_controls = get_number_input("number of controls for this amp (switches, knobs, etc ) eg: 2")
    control_names = []
    controls = []
    for i in range(num_controls):
        print("Control ", i+1, " name eg: volume or channel")
        c_name = input().lower()
        num_cap = get_number_input("number of captures for control:" + c_name)
        control_values = []
        for j in range(num_cap):
            print("name of ",c_name," position ", str(j), "eg: high or 4 or on or blue")
            cap_name = input().lower()
            control_values.append(c_name+"_"+cap_name)
        controls.append(control_values)
        control_names.append([c_name])
    # create folder, write metadata
    output_dir = amp_brand+"_"+amp_model
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        pass
    metadata = {"amp_brand":amp_brand, "amp_model":amp_model, "amp_year":amp_year, "tags":tags,
            "num_controls": num_controls, "control_names": control_names, "controls": controls,
            "includes_cab": mic_or_loadbox }
    json.dump(metadata, open(os.path.join(output_dir, "metadata.json"), "w"))

    # now know all the details, check and then run
    print("check level at max gain, will play sweep on enter")
    if repeat_or_continue("level test"):
        subprocess.run("jack_playrec {cab_ir_wav} system:playback_{training_output}".format(cab_ir_wav=cab_sweep_wav,
            training_output=training_output), shell=True)

    for control_set in itertools.product(*controls):
        control_set_name = "-".join(control_set)
        output_wav = "-".join([amp_brand, amp_model, control_set_name])
        output_wav = os.path.join(output_dir, output_wav +".wav").replace(" ", "_")
        while True:
            if repeat_or_continue(output_wav):
                print("capturing now")

                subprocess.run("jack_playrec --output-file={output_wav} {training_wav} system:playback_{training_output} system:capture_{audio_input}".format(training_wav=training_wav, output_wav=output_wav,
                    training_output=training_output, audio_input=audio_input), shell=True)
                print("capturing done")
                print("r enter to repeat, enter for continue")
                if input() != "r":
                    break
            else:
                break

    print ("capturing IR")
    while True:
        if repeat_or_continue("ir capture"):
            print("Cab brand")
            cab_brand = input().lower()
            print("Cab model")
            cab_model = input().lower()
            audio_input = mic_input
            output_wav = "-".join([cab_brand, cab_model])
            output_wav = os.path.join(output_dir, output_wav +".wav").replace(" ", "_")
            subprocess.run("jack_playrec --output-file={output_wav} {cab_ir_wav} system:playback_{training_output} system:capture_{audio_input}".format(cab_ir_wav=cab_ir_wav, output_wav=output_wav,
                training_output=training_output, audio_input=audio_input), shell=True)
            output_wav = "-".join([cab_brand, cab_model])
            output_wav = os.path.join(output_dir, output_wav +"sweep.wav").replace(" ", "_")
            subprocess.run("jack_playrec --output-file={output_wav} {cab_ir_wav} system:playback_{training_output} system:capture_{audio_input}".format(cab_ir_wav=cab_sweep_wav, output_wav=output_wav,
                training_output=training_output, audio_input=audio_input), shell=True)
            print("r enter to repeat, enter for continue")
            if input() != "r":
                break
        else:
            break


    print("Amp Done. Next amp")
