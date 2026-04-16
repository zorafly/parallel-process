#!/usr/bin/env python3

import sys, subprocess, os, threading, queue, re

info="""
WORKER:  {}
INPUT:   {}
COMMAND: {}
"""
syntax="""Syntax: 
parallel_process.py [-d] <input root> <input pattern> <threads> <command>

Options:
	-d			Dry run - don't actually execute the command

Command format specifiers:
	{path}			Full path to input file
	{path_stripped}		Path to input file, no file extension
	{filename}		Only filename, including extension
	{filename_stripped}	Only filename, no extension

Examples:

	Transcode a tree of FLAC files to AAC. Output each new file to the same
	directory as its input. Utilize 6 worker threads.
````
parallel_process.py /home/user/Music '^.*\\.flac$' 6 \\
	ffmpeg -i {path} -c:a aac -b:a 128k {path_stripped}.m4a
````

	Resize a tree of JPEG images. Images are named as follows:
	0000.png, 0001.png, ...
	Output each new file to a single, specified output directory. 
	Utilize 4 worker threads.
````
parallel_process.py /home/user/Renders/xyz '^.*[0-9]{4}\\.(jpg|jpeg)$' 4 \\
	convert {path} -resize 128x128 /mnt/output/thumbnails/{filename}
````
"""

#Strip file extension
def strip_ext(filename):
    i = len(filename) - 1
    p = filename[i]
    while i:
        if filename[i] == '.':
            break
        i -= 1
    if i:
        return filename[:i]
    return filename

#One worker iteration
def worker_dispatch(workerid, inputs, outfd, command, dry):
    #Pull one item from the work queue
    try:
        path = inputs.get(False, 0)
    except queue.Empty:
        return
    if not len(path):
        return
    
    #Build constants for command formatting
    filename = os.path.basename(path)
    filename_stripped = strip_ext(filename)
    path_stripped = os.path.dirname(path) + filename_stripped
    
    #Build command
    formatted = command.format(path = path,
                               filename = filename,
                               filename_stripped = filename_stripped,
                               path_stripped = path_stripped)
    print(info.format(workerid, path, formatted))

    #Execute command
    if not dry:
        p = subprocess.Popen(formatted, shell=True,
                             stdin=None, stdout=outfd, stderr=outfd)
        p.wait()
    return

#One worker thread
def worker(workerid, inputs, outfd, command, dry):
    while not inputs.empty():
        worker_dispatch(workerid, inputs, outfd, command, dry)
    print("Worker {} is done".format(workerid))

#Check syntax
if len(sys.argv) < 5:
    print(syntax)
    sys.exit(1)

#Check for dry-run mode
if sys.argv[1] == "-d":
    dry = 1
    args = sys.argv[1:]
else:
    dry = 0
    args = sys.argv
#Root directory containing all paths to input files
indir = args[1]
#Regular expression to select input files
inpattern = args[2]
#Number of worker threads to launch
cores = int(args[3])
#Command to run for each input file
command = " ".join(args[4:])

#Build list of inputs
def walk_error(err):
    print("Tree walk error: {}".format(err))
filenames = []
pattern = re.compile(inpattern)
for root, dirs, files in os.walk(indir, onerror=walk_error):
    here = [os.path.join(root, f) for f in files]
    matched = [f for f in here if pattern.match(f)]
    filenames += matched
print(matched)

#Build threadsafe work queue
worker_inputs = queue.Queue(maxsize=len(filenames))
for filename in filenames:
    worker_inputs.put(filename)

#Open worker logfiles
workerfds = []
for i in range(cores):
    logname="{}-worker-{}.log".format(os.path.basename(sys.argv[0]), i)
    logpath=os.path.join(os.path.realpath("."), logname)
    workerfds.append(open(logpath, "w+"))

#Start workers
workers = []
for i in range(cores):
    t = threading.Thread(target=worker,
                         args=(i, worker_inputs, workerfds[i], command, dry))
    workers.append(t)
    workers[i].start()
    
#Wait for workers to finish
for i in range(cores):
    workers[i].join()
    workerfds[i].close()

print("DONE")
