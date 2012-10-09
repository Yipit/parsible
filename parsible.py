#!/bin/python
import sys, time, os, signal, imp, argparse, logging, traceback

class Parsible(object):
    def import_plugins(self):
        # Initialize our lists
        self.processors = []

        # Map our directory names to the prefixes on methods we want to check out.
        plugin_mappings = {
                            'parsers' : 'parse',
                            'processors' : 'process'
                          }

        # Figure out where we are and start looking for plugins
        current_file = os.path.abspath(__file__)
        current_directory = os.path.abspath(os.path.join(current_file, os.path.pardir))
        plugins_directory = current_directory + "/plugins"

        # Iterate through our potential plugin locations so we can import everything
        # IMPORTANT:  Without this block we can't use the buzzword 'Autodiscover', very necessary
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
                            # Figure out what we should do with our newly discovered methods
                            if "parse" in plugin_mappings[plugin_type]:
                                if self.parser is not None:
                                    if method == self.parser:
                                        setattr(self, "parsing_function", getattr(_temp, method))
                                else:
                                    # Set the first parser we find, overwrite this laster if we find one specified
                                    setattr(self, "parsing_function", getattr(_temp, method))
                            # Construct our list of processing functions that we will call on each parsed line
                            elif "process" in plugin_mappings[plugin_type]:
                                self.processors.append(getattr(_temp, method))

    def set_logging(self):
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(asctime)s - %(message)s')
        logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
        self.logger = logging.getLogger('parsible')
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)


    def __init__(self, input_file, parser, pid_file, debug, batch, auto_reload):
        self.debug = debug
        self.batch = batch
        self.auto_reload = auto_reload
        self.set_logging()
        # Some messy business to import unknown files at runtime, cool stuff inside
        self.parser = parser
        self.import_plugins()
        # Keep internal references to these so we can change and refresh them properly
        self.input_file = input_file
        self.pid_file = pid_file

    def parsible_exit(self, status):
        os.remove(self.pid_file)
        sys.exit(status)

    def load_file(self):
        try:
            self.log_file = open(self.input_file)
        except IOError:
            print "Unable to open log file"
            self.parsible_exit(1)

    def reload_file(self, signum, frame):
        self.log_file.close()
        self.load_file()
        return

    def reload_file_if_changed(self):
        # Get the Inode for our current file
        loaded_file_inode = os.fstat(self.log_file.fileno()).st_ino

        # Check the inode of the file path that was specified
        current_file = open(self.input_file)
        current_file_inode = os.fstat(current_file.fileno()).st_ino
        current_file.close()

        # Reload if there is a discrepancy
        if loaded_file_inode != current_file_inode:
            self.reload_file(None, None)
            self.logger.debug('Log File Changed, Reloading...')
        else:
            self.logger.debug('Log File Unchanged')
        return

    def _get_current_byte_position(self):
        return self.log_file.tell()

    def _get_file_byte_length(self):
        return os.path.getsize(self.input_file)

    def _run_periodic_functions(self):
        """
        Functions that need to be run periodicly for system statistics,
        such as logging the current file progression.
        """
        current = self._get_current_byte_position()
        size = self._get_file_byte_length()
        percent = ( float(current) / float(size) ) * 100
        self.logger.error('File Statistics: Current Byte Location {current}'.format(current=current))
        self.logger.error('File Statistics: Current File Byte Size {size}'.format(size=size))
        self.logger.error('File Statistics: Processed Percentage {percent:.2f} %'.format(percent=percent))

    def set_pid_file(self):
        # All this to set up a PID file
        f = open(self.pid_file, 'w')
        PID = str(os.getpid())
        f.write(PID)
        f.flush()
        f.close()
        # Set up a callback for SigUSR1 (kill -30 or kill -USR1)
        signal.signal(signal.SIGUSR1, self.reload_file)

    def follow(self):
        # Shamelessly drafted from http://www.dabeaz.com/generators/Generators.pdf
        empty_iterations = 0
        tick = 0

        if not self.batch:
            # Go to the end of the file for tailing, otherwise we start at the beginning
            self.log_file.seek(0,2)
        while True:
            # Get our latest line (via a Generator) or None if nothing new is in place
            line = self.log_file.readline()
            if not line:
                if self.batch:
                    self.logger.debug('Ending Batch Run')
                    raise StopIteration
                if self.debug:
                    self.logger.debug('Tick Tock, waited for {} iterations'.format(empty_iterations))
                # Essentially spinlock on our logfile waiting for updates to become available
                # Depending on update speed this iteration time can be decreased
                empty_iterations += 1
                time.sleep(0.1)

                if self.auto_reload:
                    # If waiting for new lines, check once per 10 seconds to reload
                    if empty_iterations > 100:
                        empty_iterations = 0
                        self.reload_file_if_changed()
                continue

            empty_iterations = 0
            tick += 1
            tick = tick % 100
            if tick == 0:
                # Check every 100 iterations
                self._run_periodic_functions()
            # Yield so we can be called as a generator, decoupling the waiting issues.
            # Our parsing function can be evaluated later
            yield self.parsing_function(line)

    def run_processors(self, line):
        for process in self.processors:
            try:
                process(line)
            except Exception, e:
                # We can add some custom logic if needed, such as counting how many lines have issues
                # For now we just swallow errors, since the spice must flow, err parsing must continue.
                if self.debug:
                    self.logger.debug(e)
                    traceback.print_exc(file=sys.stdout)
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
            if self.debug:
                self.logger.debug(parsed_line)
            self.run_processors(parsed_line)

        # We probably will never reach here, but it pays to be tidy just in case we change code in the future
        self.log_file.close()
        self.parsible_exit(0)

if __name__ == '__main__':

    # Just setting up command line arguments.
    # Only thing interesting here is the defaults set for some options. You can skip this trying to get to the meat.
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
                         help='Name of the parsing method to use, should start with "parse_", Ex: parse_nginx   If this is not set, Parsible will use the first parser found.',
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

    cmdline.add_argument('--debug',
                         '-d',
                         action='store',
                         help='Enable Debugging',
                         dest='debug',
                         default=False
                        )

    cmdline.add_argument('--batch-mode',
                         '-b',
                         action='store',
                         help='If Set, Parsible will start at the top of the log file and exit once it reaches the end.  Useful for processing logs that are not realtime',
                         dest='batch',
                         default=False
                        )

    cmdline.add_argument('--auto-reload',
                         '-a',
                         action='store',
                         help='If Set, when receiving empty lines Parsible will check if there is a discrepancy between the stored and existing file descriptors for the log file. If a discrepancy is found, Parsible will reload the new file.',
                         dest='auto_reload',
                         default=False
                        )

    args = cmdline.parse_args()
    p = Parsible(args.input_file, args.parser, args.pid_file, args.debug, args.batch, args.auto_reload)
    p.main()
