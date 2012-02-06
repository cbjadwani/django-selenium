from optparse import make_option
import sys

from django.conf import settings
from django.core.management.commands import test
from django.test.utils import get_runner

from django_selenium import settings as selenium_settings


class Command(test.Command):
    # TODO: update when django 1.4 is out, it will have custom options available
    option_list = test.Command.option_list + (
        make_option('--selenium', action='store_true', dest='selenium', default=False,
            help='Run selenium tests during test execution\n'
                 '(requires access to 4444 and $SELENIUM_TESTSERVER_PORT ports, java and running X server'),
        make_option('--selenium-only', action='store_true', dest='selenium_only', default=False,
            help='Run only selenium tests (implies --selenium)')
    )

    def fix_test_db_setting(self):
        # If sqlite3 engine is used we need to update the test db setting
        # because sqlite3 ':memory:' db does not allow multiple connections.
        # Django defualts to use the fast ':memory:' db for tests but it
        # can not be used as the selenium test server is run in a seperate
        # thread which create a new connection to the db.
        # Django 1.4 will fix this by adding support for sharing a single
        # connection across threads.

        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
        import os.path

        for db_name, db_settings in settings.DATABASES.items():
            if db_settings['ENGINE'].split('.')[-1] == 'sqlite3':
                test_name = db_settings.get('TEST_NAME')
                if test_name is None:
                    dirname, filename = os.path.split(db_settings['NAME'])
                    filename = 'test_' + filename
                    test_name = os.path.join(dirname, filename)
                    db_settings['TEST_NAME'] = test_name
                elif test_name == ':memory:':
                    msg = 'settings[%r][%r] = %r\n' \
                            '  Can not use ":memory:" when running selenium '\
                            'tests' % (db_name, 'TEST_NAME', test_name)
                    raise ImproperlyConfigured(msg)

    def handle(self, *test_labels, **options):

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)
        failfast = options.get('failfast', False)
        selenium = options.get('selenium', False)
        selenium_only = options.get('selenium_only', False)
        if selenium_only:
            selenium = True

        if selenium:
            self.fix_test_db_setting()

        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast,
                                 selenium=selenium, selenium_only=selenium_only)
        failures = test_runner.run_tests(test_labels)
        if failures:
            sys.exit(bool(failures))
