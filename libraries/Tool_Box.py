"""
Tool_Box v0.3.0
    Aug. 6, 2018
    Dennis A. Simpson
    Options file parser is no longer a class and now returns an updated argparse object.  This library needs a good
    scrubbing.
Tool_Box v0.2.1
    October 12, 2017
    Dennis A. Simpson
    Updated the options file parser.
Tool_Box v0.2.0
    June 9, 2017
    Dennis A. Simpson
    Added the class CoverageCalculator, the decorator class depreciated, and function debug_messenger.
Tool_Box v0.1.0
    May 22, 2017
    Dennis A. Simpson
    Initial setup of module.  Intended to contain various general functions that can be applied to many programs.
@author: Dennis A. Simpson
         University of North Carolina at Chapel Hill
         Chapel Hill, NC  27599
@copyright: 2019
"""

import csv
import os
from collections import namedtuple
import collections
import platform
import inspect
import sys
import getpass
import socket
import logging
import gzip
from datetime import datetime
from contextlib import suppress
import re
# import magic
# import pkg_resources as resource

__author__ = 'Dennis A. Simpson'
__version__ = "0.3.0"


def __infile(self):

    # mime_type = magic.from_file(self.input_file, mime=True)
    mime_type =""

    if "text" in mime_type:
        fq_file = open(self.input_file, 'rU')
    elif "gzip" in mime_type:
        fq_file = gzip.open(self.input_file, 'rt', encoding='utf-8')
    else:
        self._log.warning("Unsupported file-type for {0}.  Only TEXT or GZIP Allowed.".format(self.input_file))
        raise SystemExit(1)
    return fq_file


def delete(file_list):
    """
    Delete one or more files.
    :param file_list:
    :return:
    """
    for file in file_list:
        if os.path.isfile(file):
            with suppress(FileNotFoundError):
                os.remove(str(file))


def sort_dict(key_counts):
    return sorted(key_counts.items(), key=lambda x: (-1 * x[1], x[0]))


def compress_files(file, log):
    """
    This function will compress our files.  Takes a very long time.
    :param file:
    :param log:
    :return:
    """
    # ToDo: Consider allowing user access to gzip compression level.
    if os.path.isfile(file):
        exists_list = [file + ".gz"]
        delete(exists_list)  # if the compressed file already exists we need to delete it first.
    cmd = "gzip -9 " + file
    os.system(cmd)
    log.debug("{0} Compressed".format(file))

    return


def chromosomes(species, log, include_chrY):
    """
    Little ditty to generate a list of chromosome names.
    :param include_chrY:
    :param species:
    :param log:
    :return:
    """
    chrom_list = ["chrX", "chrMT"]
    count = 0
    if species == "Mouse":
        # chrom_list = ["chrX", "chrMT"]
        count = 20
    elif species == "Human":
        # chrom_list = ["chrX", "chrM"]
        count = 23
    else:
        log.error("Species Must be Mouse or Human")

    for i in range(1, count):
        chrom_list.append("chr{0}".format(i))
    if include_chrY:
        chrom_list.append("chrY")

    return chrom_list


def peak_memory():
    """
    This will return the peak memory used in Mb for the segment called.
    :return:
    """
    return 0
    peak_memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    if platform.system() == 'darwin':
        peak_memory_mb /= 1024

    return int(peak_memory_mb)


class UsageError(Exception):
    """
    All problems with the --options_file or commands come through here.
    """

    def __init__(self, msg, *args):
        super(UsageError, self).__init__(msg, *args)


class Logger:
    _DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    _FILE_LOG_FORMAT = '%(asctime)s|%(levelname)s|%(start_time)s|%(host)s|%(user)s|%(message)s'
    _CONSOLE_LOG_FORMAT = '%(asctime)s|%(levelname)s|%(message)s'

    def __init__(self, args, console_stream=None, parellel_id=None):
        self._verbose = args.Verbose
        if parellel_id:
            log_file = "{}_{}".format(args.Job_Name, parellel_id)
        else:
            log_file = args.Job_Name

        self._log_filename = "{0}{1}.log".format(args.WorkingFolder, log_file)

        try:
            log = open(self._log_filename, "w")
            log.close()

        except IOError:
            raise UsageError('Cannot create log file [{0}]. Review inputs and try again.'.format(self._log_filename))

        if console_stream:
            self._console_stream = console_stream
        else:
            self._console_stream = sys.stderr
        # self._console_stream = logging.StreamHandler(console_stream)
        user = getpass.getuser()
        host = socket.gethostname()
        start_time = datetime.now().strftime(Logger._DATE_FORMAT)

        self._logging_dict = {'user': user,
                              'host': host,
                              'start_time': start_time}

        logging.basicConfig(format=Logger._FILE_LOG_FORMAT,
                            level=args.Verbose,
                            datefmt=Logger._DATE_FORMAT,
                            filename=self._log_filename)

        self._file_logger = logging
        self.warning_occurred = False

    def _print(self, level, message, args):
        now = datetime.now().strftime(Logger._DATE_FORMAT)
        print(Logger._CONSOLE_LOG_FORMAT % {'asctime': now, 'levelname': level, 'message': self._format(message, args)},
              file=self._console_stream)
        self._console_stream.flush()

    @staticmethod
    def _format(message, args):
        try:
            log_message = message.format(*[i for i in args])
        except IndexError as err:
            log_message = "Malformed log message ({}: {})""|{}|{}" \
                .format(type(err).__name__, err, message, [str(i) for i in args])

        return log_message

    def debug(self, message, *args):
        if self._verbose == "DEBUG":
            self._print("\033[96mDEBUG\033[m", message, args)

        self._file_logger.debug(self._format(message, args), extra=self._logging_dict)

    def _log(self, msg_type, method, message, *args):
        self._print(msg_type, message, args)
        method(self._format(message, args), extra=self._logging_dict)

    def error(self, message, *args):
        self._log("\033[38;5;202mERROR\033[m", self._file_logger.error, message, *args)

    def info(self, message, *args):
        self._log("\033[38;5;220mINFO\033[m", self._file_logger.info, message, *args)

    def warning(self, message, *args):
        self._log("\033[1;31mWARNING\033[m", self._file_logger.warning, message, *args)
        self.warning_occurred = True


def log_environment_info(log, args, command_line_args):
    log.info("original_command_line|{}".format(' '.join(command_line_args)))
    log.info('command_options|{}'.format(args))
    log.info('WorkingFolder|{}'.format(args.WorkingFolder))
    log.info('platform_uname|{}'.format(platform.uname()))
    log.info('platform_python_version|{}'.format(platform.python_version()))


def debug_messenger(reason: str = None):
    """
    Simple call for debugging that will print the filename and line number to the screen.
    :param reason:
    :return:
    """

    if reason is None:
        reason = "Programmer Neglected to Enlighten Us About the Need for Debugging This Section."

    frameinfo = inspect.getframeinfo(inspect.currentframe().f_back)
    print("\033[1;31m***WARNING: Debugging Module {0} at Line {1}.\n\t-->REASON: {2}\033[m"
          .format(frameinfo.filename, frameinfo.lineno, reason))


def options_file(options_parser):
        """
        This function parses the options file and adds the data to the argparse object.
        :param: options_parser
        :return:
        """
        count = 0
        config_file = options_parser.parse_args().options_file

        if not os.path.isfile(config_file):
            print("\033[1;31mWARNING:\n\tOptions_File {} Not Found.  Check File Name and Path.".format(config_file))
            raise SystemExit(1)

        options = csv.reader(open(config_file), delimiter='\t')

        for line in options:
            count += 1
            if len(line) < 2 or "#" in str(line[0]):  # Skip lines that are comments or blank.
                continue

            try:
                value = re.sub(r"[\s]", "", line[1].split("#")[0])  # Strip out any end of line comments and whitespace.

            except IndexError:
                raise SystemExit("There is a syntax error in the options file on line " .format(count))

            key = line[0].strip('--')
            options_parser.add_argument(line[0], dest=key, default=value)

        return options_parser


class FileParser:
    @staticmethod
    def options_file(options_file):
        """
        This function parses the file and returns an object.
        :return:
        """
        count = 0
        options_dictionary = collections.defaultdict(str)

        if not os.path.isfile(options_file):
            print("\033[1;31mWARNING:\n\tOptions_File {} Not Found.  Check File Name and Path.".format(options_file))
            raise SystemExit(1)

        options = csv.reader(open(options_file), delimiter='\t')

        for line in options:
            count += 1
            if len(line) < 2 or "#" in str(line[0]):  # Skip lines that are comments or blank.
                continue

            try:
                value = re.sub(r"[\s]", "", line[1].split("#")[0])  # Strip out any end of line comments and whitespace.

            except IndexError:
                raise SystemExit("There is a syntax error in the options file on line " .format(count))

            key = line[0].strip('--')
            options_dictionary[key] = value

        return namedtuple('options_file', options_dictionary.keys())(**options_dictionary)

    @staticmethod
    def indices(log, input_file):
        """
        Parse the index file or target file and return a list of values.
        :return:
        """
        log.info("Parsing {}".format(input_file))
        if not os.path.isfile(input_file):
            log.error("{} Not Found.  Check File Name and Path.".format(input_file))
            raise SystemExit(1)

        index_list = []
        line_num = 0
        index_file = list(csv.reader(open(input_file), delimiter='\t'))
        for line in index_file:
            line_num += 1
            col_count = len(line)

            if col_count > 0 and len(line[0].split("#")[0]) > 0:  # Skip any lines that are blank or comments.
                tmp_line = []

                for i in range(col_count):
                    try:
                        line[i] = line[i].split("#")[0]  # Strip out end of line comments and white space.
                    except IndexError:
                        raise SystemExit("There is a syntax error in file {0} on line {1}, column {2} "
                                         .format(input_file, str(line_num), str(i)))

                    line[i] = re.sub(",", '', line[i])  # Strip out any commas.

                    tmp_line.append(line[i])
                index_list.append(tmp_line)

        log.debug("Parsing Complete for  {}".format(input_file))

        return index_list
