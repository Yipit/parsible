#!/bin/python
import sys, time, os, signal, imp, argparse

class Parsible(object):
    def import_plugins(self):
        # Initialize our lists
        self.processors = []
        
        current_file = os.path.abspath(__file__)
        current_directory = os.path.abspath(os.path.join(current_file, os.path.pardir))
        plugins_directory = current_directory + "/plugins"
        
        # Map our directory names to the prefixes on methods we want to check out.
        plugin_mappings = {
                            'parsers' : 'parse',
                            'processors' : 'process',
                            'outputs' : 'output'
                          }

        for plugin_type in plugin_mappings.keys():
            directory = plugins_directory + "/" + plugin_type
            for f in os.listdir(directory):
                if f.endswith(".py") and not f.startswith("_"):
                    # Get the name of the file for importing
                    parser_file = f.rpartition(".")[0]
                    # Import the file so we can inspect the methods inside
                    __import__('plugins.%s.%s' % (plugin_type, parser_file))
                    for method in dir(sys.modules["plugins.%s.%s" % (plugin_type, parser_file)]):
                        # Filter down to methods that have the appropriate prefix
                        if method.startswith(plugin_mappings[plugin_type]):
                            _temp = __import__('plugins.%s.%s' % (plugin_type, parser_file), globals(), locals(), [method], -1)
                            if "parse" in plugin_mappings[plugin_type]:
                                if self.parser is not None:
                                    if method == self.parser:
                                        setattr(self, "parsing_function", getattr(_temp, method))
                                else:
                                    # Currently this will overwrite any previously found parsing functions, NBD
                                    setattr(self, "parsing_function", getattr(_temp, method))
                            # Construct our list of processing functions that we will call on each parsed line
                            elif "process" in plugin_mappings[plugin_type]:
                                self.processors.append(getattr(_temp, method))

    def __init__(self, input_file, parser, pid_file):
        # Some messy business to import unknown files at runtime
        self.parser = parser
        self.import_plugins()
        # Keep internal references to these so we can change and refresh them properly
        self.input_file = input_file
        self.pid_file = pid_file  

    def exit(self, status):
        os.remove(self.pid_file)
        sys.exit(status)

    def load_file(self):
        try:
            self.log_file = open(self.input_file)
        except IOError:
            print "Unable to open log file"
            exit(1)

    def reload_file(self, signum, frame):
        self.log_file.close()
        self.load_file()
        return

    def set_pid_file(self):
        f = open(self.pid_file, 'w')
        PID = str(os.getpid())
        f.write(PID)
        f.flush()
        f.close()
        # Set up a callback for SigUSR1 (kill -30 or kill -USR1)
        signal.signal(signal.SIGUSR1, self.reload_file)

    def follow(self):
        # Shamelessly drafted from http://www.dabeaz.com/generators/Generators.pdf
        # Go to the end of the file
        self.log_file.seek(0,2)
        while True:
            # Get our latest line (via a Generator) or None if nothing new is in place
            line = self.log_file.readline()
            if not line:
                # Essentially spinlock on our logfile, depending on update speed this can be lowered
                time.sleep(0.1)
                continue
            # Yield so we can be called as a generator, decoupling the waiting issues.
            # Our parsing function can be evaluated later
            yield self.parsing_function(line)

    def run_processors(self, line):
        for process in self.processors:
            try:
                process(line)
            except:
                # We can add some custom logic if needed, such as counting how many lines have issues
                continue

    def main(self):
        # Being a good UNIX Citizen
        self.set_pid_file()
        self.load_file()

        # Get our Generator Reference
        parsed_log_file = self.follow()

        # Abstract all the messy generator logic away into a simple for-each
        for parsed_line in parsed_log_file:
            # The processors should take care of outputting data as they see fit
            self.run_processors(parsed_line)
        
        # We probably will never reach here, but it pays to be tidy just in case
        self.log_file.close()

if __name__ == '__main__':

    cmdline = argparse.ArgumentParser(usage="usage: parsible.py --log-file /var/log/mylog [options]",
                                      description="Tail a log file and filter each line to generate metrics that can be output to any desired endpoint.")

    cmdline.add_argument('--log-file', 
                         '-l', 
                         action='store',
                         help='The absolute path to the log file to be parsed, Ex: /var/log/mylog',
                         dest='input_file',
                         required=True
                        )

    cmdline.add_argument('--parser', 
                         '-p', 
                         action='store',
                         help='Name of the parsing method to use, should start with "parse_", Ex: parse_nginx',
                         dest='parser',
                         default=None
                        )

    cmdline.add_argument('--pid-file', 
                         '-f', 
                         action='store',
                         help='Absolute path to use for the PID file, Ex: /tmp/parsible.pid',
                         dest='pid_file',
                         default='/tmp/parsible.pid'
                        )

    args = cmdline.parse_args()
    import pdb; pdb.set_trace()
    p = Parsible(args.input_file, args.parser, args.pid_file)
    p.main()
