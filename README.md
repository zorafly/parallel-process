This script enumerates a tree of input files, matches each path against a
regular expression, and performs a command for each result. I eventually got
around to making this so I don't have to make hacky, specialized bash/sed
scripts anymore.

Syntax: 
parallel_process.py [-d] <input root> <input pattern> <threads> <command>

Options:
        -d                      Dry run - don't actually execute the command

Command format specifiers:
        {path}                  Full path to input file
        {path_stripped}         Path to input file, no file extension
        {filename}              Only filename, including extension
        {filename_stripped}     Only filename, no extension

Examples:

        Transcode a tree of FLAC files to AAC. Output each new file to the same
        directory as its input. Utilize 6 worker threads.
````
parallel_process.py /home/user/Music '^.*\.flac$' 6 \
        ffmpeg -i {path} -c:a aac -b:a 128k {path_stripped}.m4a
````

        Resize a tree of JPEG images. Images are named as follows:
        0000.png, 0001.png, ...
        Output each new file to a single, specified output directory. 
        Utilize 4 worker threads.
````
parallel_process.py /home/user/Renders/xyz '^.*[0-9]{4}\.(jpg|jpeg)$' 4 \
        convert {path} -resize 128x128 /mnt/output/thumbnails/{filename}
````

