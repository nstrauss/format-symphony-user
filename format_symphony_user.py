#!/usr/bin/python

'''format_symphony_user.py
Text manipulation tool to take a properly formatted CSV containing user data
and convert to SirsiDynix Symphony supported ASCII LDUSER format. To be used to
create and update users with load users report.

Option to upload resulting text file to SFTP server with -sftp flag.

Required columns:
    - student_id
    - first_name
    - last_name
    - birthdate
    - grade
    - grad_year
    - street
    - city
    - state
    - zip
    - email
    - phone_number

Fields should be all caps when possible except for email.
Expected phone number format (555)555-5555 as that's what our SIS provides.

Last 10 runs will be kept in generated_ascii. Older files are deleted.'''

import argparse
import csv
import operator
import os
import platform
import sys
from collections import OrderedDict
from configparser import ConfigParser
from datetime import datetime
from shutil import copyfile

import pysftp

__version__ = '0.5.0'

# Global config file path.
CFG_DIR = os.path.join(sys.path[0], 'config')
CFG_PATH = os.path.join(CFG_DIR, 'symphony.conf')
config = ConfigParser()
config.read(CFG_PATH)

# Global paths.
CSV_NAME = config.get('filenames', 'csv_name')
ASCII_NAME = config.get('filenames', 'ascii_name')
CSV_PATH = os.path.join(sys.path[0], CSV_NAME)
ASCII_DIR = os.path.join(sys.path[0], 'generated_ascii')
ASCII_DEST = os.path.join(sys.path[0], ASCII_NAME)

# Time stamp and generic I/O error message.
TIMESTAMP = str(datetime.today().strftime('%Y%m%d-%H%M%S'))
PERM_ERROR = 'Failed to write to file. Check permissions. Exiting.'


def write_value(file, field, value):
    '''Write ASCII formatted value.'''
    # Strip trailing whitespace. ASCII format hates trailing whitespace.
    value = value.rstrip()
    try:
        file.write('.' + field + '.')
        markers = ['_BEGIN', '_END']
        if any(x in field for x in markers):
            file.write('\n')
        else:
            file.write('   ' + '|' + 'a' + value + '\n')
    except (IOError, OSError):
        print(PERM_ERROR)
        exit(1)


def transform_zip(number):
    '''Get rid of extended format ZIP code.'''
    zip_code = number.split('-')[0]
    return zip_code


def transform_phone(number):
    '''Expected phone number format (555)555-5555. Changes to spaces only.'''
    phone = number.replace('(', '').replace(')', ' ').replace('-', ' ')
    return phone


def get_grad_year(year, grade):
    '''Use provided grad year if available. Otherwise approximate based
    on grade level and current year. Not perfect, but value will generally
    be available once student closer to graduation.'''
    if year != '':
        year = year
    else:
        curr_year = int(datetime.today().strftime('%Y'))
        years_to_grad = 12 - int(grade)
        year = years_to_grad + curr_year
    return str(year)


def copy_report(file):
    '''Copy file from generated_ascii folder to main folder.'''
    try:
        copyfile(file, ASCII_DEST)
    except (IOError, OSError):
        print(PERM_ERROR)
        exit(1)


def creation_date(path_to_file):
    '''Try to get the date that a file was created, falling back to when
    it was last modified if that isn't possible. See
    http://stackoverflow.com/a/39501288/1709587 for explanation.'''
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def report_dates(report_dir):
    '''Get dict of report files and created timestamp.'''
    report_dates = {}
    for report in os.listdir(report_dir):
        if report.endswith('.txt'):
            date = int(creation_date(os.path.join(report_dir, report)))
            report_dates[report] = date
    return report_dates


def upload_ftp_file(ascii_file):
    '''Connect to SirsiDynix SFTP server specified in config file and upload
    converted ASCII formatted user data.'''
    # Define variables from config file.
    server = config.get('sftp', 'server')
    port = (config.getint('sftp', 'port'))
    username = config.get('sftp', 'user')
    password = config.get('sftp', 'password')
    known_hosts = config.get('sftp', 'host_file')
    known_hosts_file = os.path.join(CFG_DIR, known_hosts)
    disable_key_check = (config.getboolean('sftp', 'disable_key_check'))

    # Open connection. Set cnopts to verify host key. Set True to skip.
    cnopts = pysftp.CnOpts()
    if disable_key_check is True:
        cnopts.hostkeys = None
    else:
        cnopts.hostkeys.load(known_hosts_file)

    try:
        srv = pysftp.Connection(host=server,
                                port=port,
                                username=username,
                                password=password,
                                cnopts=cnopts)
    except Exception as e:
        err = str(e)
        print(err)
        exit(1)

    # Copy file to FTP server, preserve modification time.
    srv.put(ascii_file, preserve_mtime=True)

    # Closes the connection
    srv.close()


def main():
    '''Do the main thing here'''
    # Add command line argument for SFTP upload.
    parser = argparse.ArgumentParser()
    parser.add_argument('-sftp', '--sftp', action='store_true',
                        help='Upload resulting ASCII user data via SFTP')
    parser.add_argument('-v', '--version', action='version',
                        version=__version__)
    args = parser.parse_args()

    # Check to see if ASCII_DIR exists. If not create.
    if not os.path.exists(ASCII_DIR):
        try:
            os.mkdir(ASCII_DIR)
        except (IOError, OSError):
            print(PERM_ERROR)
            exit(1)

    # Generate timestamped file to append user ASCII.
    ascii_path = os.path.join(ASCII_DIR, 'LDUSER-' + TIMESTAMP + '.txt')
    try:
        ascii_file = open(ascii_path, 'w+', newline='\n')
    except (IOError, OSError):
        print(PERM_ERROR)
        exit(1)

    # Loop through CSV to append user values to LDUSER form.
    with open(CSV_PATH) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Get modified values as needed.
            zip_code = transform_zip(row['zip'])
            phone_number = transform_phone(row['phone_number'])
            grad_year = get_grad_year(row['grad_year'], row['grade'])
            user_id = config.get('data', 'id_prefix') + row['student_id']

            ascii_file.write('*** DOCUMENT BOUNDARY ***\nFORM=LDUSER\n')
            ascii_record = OrderedDict([
                ('USER_ID', user_id),
                ('USER_ROUTING_FLAG', config.get('data', 'USER_ROUTING_FLAG')),
                ('USER_FIRST_NAME', row['first_name']),
                ('USER_LAST_NAME', row['last_name']),
                ('USER_NAME_DSP_PREF', config.get('data', 'USER_NAME_DSP_PREF')),
                ('USER_BIRTH_DATE', row['birthdate']),
                ('USER_LIBRARY', config.get('data', 'USER_LIBRARY')),
                ('USER_PROFILE',  config.get('data', 'USER_PROFILE')),
                ('USER_PIN', user_id[-4:]),
                ('USER_ACCESS', config.get('data', 'USER_ACCESS')),
                ('USER_ENVIRONMENT', config.get('data', 'USER_ENVIRONMENT')),
                ('USER_CATEGORY1', config.get('data', 'USER_CATEGORY1')),
                ('USER_CATEGORY11',  config.get('data', 'USER_CATEGORY11')),
                ('USER_CATEGORY12', grad_year),
                ('USER_PRIV_EXPIRES', grad_year + config.get('data', 'expire_day')),
                ('USER_STATUS', config.get('data', 'USER_STATUS')),
                ('USER_MAILINGADDR', '1'),
                ('USER_ADDR1_BEGIN', ''),
                ('STREET', row['street']),
                ('CITY/STATE', row['city'] + ' ' + row['state']),
                ('ZIP', zip_code),
                ('PHONE', phone_number),
                ('EMAIL', row['email']),
                ('USER_ADDR1_END', ''),
                ('USER_XINFO_BEGIN', ''),
                ('NOTIFY_VIA', config.get('data', 'NOTIFY_VIA')),
                ('USER_XINFO_END', ''),
                ('USER_CHG_HIST_RULE',  config.get('data', 'USER_CHG_HIST_RULE'))
            ])

            for field, value in ascii_record.items():
                write_value(ascii_file, field, value)
            ascii_file.write('\n')

    # Close file before copying to avoid I/O buffer issues.
    ascii_file.close()
    # Copy result to standard file name in main folder.
    copy_report(ascii_path)

    # Only keep latest 10 reports.
    r = report_dates(ASCII_DIR)
    sorted_r = sorted(r.items(), reverse=True, key=operator.itemgetter(1))
    for x in sorted_r[10:]:
        p = os.path.join(ASCII_DIR, x[0])
        try:
            os.remove(p)
        except (IOError, OSError):
            pass

    # Copy resulting file to configured SFTP server if flag set.
    if args.sftp is True:
        upload_ftp_file(ASCII_DEST)


if __name__ == '__main__':
    main()
