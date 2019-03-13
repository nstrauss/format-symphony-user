# SirsiDynix Symphony LDUSER Formatting
`format_symphony_user.py` is a python3 text manipulation tool that takes a properly formatted CSV containing student user data and converts to SirsiDynix Symphony supported ASCII LDUSER format. It's meant to help to create and update users with a Symphony load users report.

The goal of this is to make a general use tool that libraries can use to bulk create and update users via a CSV. This originally came about as part of a project to automate mass library card creation for students within a public school district.

SirsiDynix documentation isn't included in this repo as it's only available behind their support portal login. However, I am able to document the user fields that I found useful. Example CSV and ASCII files are also provided.

- [CSV Fields](#csv-fields)
- [symphony.conf Configurable Fields](#symphonyconf-configurable-fields)
    + [USER_CATEGORY Fields - Demographic Info](#user-category-fields---demographic-info)
- [How to Run](#how-to-run)
- [SFTP Upload](#sftp-upload)
    + [Host Key Verification](#host-key-verification)
- [Workflow](#workflow)

# CSV Fields
These are fields that change per user and are specific to scenarios dealing with student accounts. Address information defaults to USER_MAILINGADDR 1. Trailing whitespace is stripped from all values since it can create formatting issues.

- student_id
- first_name
- last_name
- birthdate - YYYYMMDD format.
- grade - No leading 0.
- grad_year - When blank will attempt to calculate based on current year and grade.
- street
- city
- state
- zip - Strips extended numbers, anything after a `-`. 
- email
- phone_number - Expected phone number format is (555)555-5555. Changes to spaces only.

# symphony.conf Configurable Fields
`/config/symphony.conf` is configurable for static values which are the same across every user record (.USER_. formatted), input and ouput filenames, and SFTP.

Not all data fields are included which can be used in user creation as documented by SirsiDynix. These are the fields found to be useful. In most cases additional fields aren't necessary.

Under filenames settings csv_name is the CSV `format_symphony_user.py` looks for in the same folder it exists. This should be set to a standard value, probably whatever the ouput of the filename from your SIS is. ascii_name is the resulting converted ASCII user records filename. Again this is a standard name so that Symphony's scheduled load user report can target the same file path. 

SFTP credentials, server address, and port are in most cases provided by SirsiDynix support when hosted. These will be different for on premise environments. 

### USER_CATEGORY Fields - Demographic Info
USER_CATEGORY fields are arbitrary demographic information. These may need to be changed depending on your environment.

# How to Run
1. Clone or copy the repo.
2. Copy CSV containing student data with required columns to main folder. 
3. Run `python ./format_symphony_user.py`
4. The resulting file will be ASCII formatted user data which can be used in a load user report. Name is whatever's set for ascii_name.
5. If SFTP flag is used and SFTP fields configured the resulting file will be uploaded to `/Unicorn/Xfer/` directory.
    * `python ./format_symphony_user.py -sftp`


# SFTP Upload
SFTP support is included using [pysftp](https://pysftp.readthedocs.io/). Modify the required `sftp` fields in `/config/symphony.conf` and then run `./format_symphony_user -sftp`. `-sftp/--sftp` is the only available argument. 

`pysftp` is not a default module so it may have to be installed using `pip install pysftp`

Default port is 822 and initial path /Unicorn/Xfer/ as that's what SirsiDynix support provided.

### Host Key Verification
Host key verification is enabled by default and recommended whenever possible. Key entries are by default read from `/config/known_hosts`. To find a server's public key use `ssh-keyscan`.

```ssh-keyscan -p 822 myhost.sirsi.net```

The result will be something like...

```[myhost.sirsi.net]:822 ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAqrBkf6KLOC7pyL4qGkpNlWS7H2fpqsexdQINf6W2apObNKzzWgoVbkO5fjpEMxsuhf97eZUqPf3BfI/Igg6Un4m0gl/7aVauI7VqQhrdlfW+yr8O34LUJneix8dSXGmBttNxgLmNmah13lYbKcRn3vdaQabQc//6+XBtoyw==```

Which then needs to be modified to an OpenSSL formatted entry. Remove brackets and port number. A properly formatted entry will look like...

```myhost.sirsi.net ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAqrBkf6KLOC7pyL4qGkpNlWS7H2fpqsexdQINf6W2apObNKzzWgoVbkO5fjpEMxsuhf97eZUqPf3BfI/Igg6Un4m0gl/7aVauI7VqQhrdlfW+yr8O34LUJneix8dSXGmBttNxgLmNmah13lYbKcRn3vdaQabQc//6+XBtoyw==```

Add that as one line to `/config/known_hosts` and then try an SFTP upload with `./format_symphony_user -sftp`. 

If necessary host key verification can be disabled by setting `disable_key_check` to `True`. But don't!

# Workflow
Export student data from SIS > Run format_symphony_user.py > ascii_converted_data.txt uploaded via SFTP to Symphony server > Load users report scheduled in Symphony to create and update users