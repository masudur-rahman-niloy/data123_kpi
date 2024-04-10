# coding: utf-8
from .base import *

LOGGING['handlers']['console'] = {
    'level': 'DEBUG',
    'class': 'logging.StreamHandler',
    'formatter': 'verbose'
}

INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')


def show_toolbar(request):
    return env.bool('DEBUG_TOOLBAR', False)


DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': show_toolbar}

ENV = 'dev'

# Expiration time in sec. after which paired data xml file must be regenerated
# Does not need to match KoBoCAT setting
PAIRED_DATA_EXPIRATION = 5

# Minimum size (in bytes) of files to allow fast calculation of hashes
# Should match KoBoCAT setting
HASH_BIG_FILE_SIZE_THRESHOLD = 200 * 1024  # 200 kB

# Chunk size in bytes to read per iteration when hash of a file is calculated
# Should match KoBoCAT setting
HASH_BIG_FILE_CHUNK = 5 * 1024  # 5 kB

# To avoid buffer to be truncated when running `runserver_plus` or `shell_plus`
# with option `--print-sql`
SHELL_PLUS_PRINT_SQL_TRUNCATE = None
RUNSERVER_PLUS_PRINT_SQL_TRUNCATE = None

CELERY_TASK_ALWAYS_EAGER = True
