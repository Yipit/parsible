# Parsible

A tool to help you parse your log files, written in [Python](http://http://python.org/).  The goal was to make a tool that will do the grunt work of following your logs in realtime, and to be easily be extended via plugins.


## Concepts
===========

There are a few core ideas we tried to bring together in Parsible:

* **Plugins**:  We wanted to make the parsers, processors, and outputs all customizable and easy to write. All plugins are autodiscovered on startup and have a very simple format for connecting them together.

* **Real Time**: Parsible will tail your log file as the lines come in, we opted away from a stateful approach where new lines are read in batches since we feel it simplifies the flow and reduces complexity.

* **Generators**:  Log files can get big, really big.  By leveraging generators Parsible can keep it's memory footprint small and independent of the size of log file. There is no hard restriction on memory, disk, or CPU usage, so be careful when writing your custom plugins. 

* **System Conventions**: Since Parsible works with logs it is wise to follow Linux logging conventions.  Parsible integrates easily with [logrotate](http://linuxcommand.org/man_pages/logrotate8.html).

## Plugins
===========

**Parsers**: We wanted to make it easy to write custom parsers for whatever type of log file you may be reading.  Your custom parser has to follow a few conventions.  A simple nginx parser has been included as an example.

1. Your parser should live inside of the `plugins/parsers` directory

2. Your parsing function should start with `parse_`, for example the included nginx parser contains a function called `parse_nginx`

3. The parsing method signature should take one parameter which will consist of one line from the log file.  You may parse the line however you see fit, we opted for a regex implementation since it fits nicely with our dictionary output format and we expect our nginx log data to be well structured.

4. The parsing method can output whatever you like, as it will be feed directly into the processing functions.  In our case we found that a dictionary works very well as lightweight storage for the parsed data although this is not required as you get to write the processing functions as well.

5. Errors from a `parse` method are swallowed by the same try/except block that handles `process` methods due to lazy evaluation.  Currently there is not recording of these occurrences although this behavior can be easily modified.

***

**Processors**: Once a line of log data is parsed it is time to do something useful with it.  You can have your processors do whatever you wish, although it is suggested that they remain stateless so that you don't have any lingering effects from feeding on large log files over the course of a day. Some sample `process` methods can be found in `plugins/outputs/url.py.`

1. Your processors should live inside of the `plugins/processors` directory

2. Your parsing function should start with `process_` so that the autoloader can find it. For example the sample processor contains  functions called `process_api` and `process_business`.

3. Your parsing method can take in whatever you please.  The output of your parsing function will be fed directly to each processor that Parsible was able to discover.

4. Outputting from parsing methods is up to you.  The suggested flow is that you import any output functions you wish to use directly and call them as needed.  

5. Any errors from a `process` method are currently swallowed and left untracked, although it is very simple to modify this behavior if desired.

***

**Outputs**: Output functions are given their own directory to simplify the structure of Parsible.  The output functions should be called directly by your code in your `process` methods, but it is cleaner to logically separate them inside the plugin system for clarity.  Parsible will not attempt to run any `output` functions directly.  For some example `output` functions check out `plugins/outputs/statsd.py` 

***

## System Conventions
======================

**Log Rotate**: We like our code to play nice with our systems, especially for a program like Parsible.

* Parsible creates a PID file in `/tmp/parsible.pid` so that it is easy to find with other programs.

* Parsible reloads the log file on receipt of the USR1 signal. This makes it easy to work with inside of [logrotate](http://linuxcommand.org/man_pages/logrotate8.html) scripts.

Here is our `logrotate` script before Parsible:

```bash
    postrotate
        [ ! -f /var/run/nginx.pid ] || kill -USR1 `cat /var/run/nginx.pid`
    endscript
```

And After

```bash
    postrotate
        [ ! -f /var/run/nginx.pid ] || kill -USR1 `cat /var/run/nginx.pid`; \
        [ ! -f /tmp/parsible.pid ] || kill -USR1 `cat /tmp/parsible.pid`
    endscript
```

### Usage
=========

```bash
parsible.py --log-file /var/log/mylog --pid-file /tmp/parsible.pid --parser parse_nginx
```

### Requirements
================

* Linux
* Python 2.7+ (due to argparse)
* Some tasty logs



