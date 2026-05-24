import pytest
import django
import os
import pytest_asyncio
from django.conf import settings

from maskinfly.audit import AuditLogger
from maskinfly.masker import Masker

try:
    import pytest_asyncio
    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False

def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_settings')
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            USE_TZ=True,
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
            INSTALLED_APPS=[],
            MIDDLEWARE=[],
            MASKINFLY={},
        )
    django.setup()

@pytest.fixture
def rf():
    from django.test.client import RequestFactory
    return RequestFactory()

@pytest.fixture
def audit_logger():
    from maskinfly.audit import AuditLogger
    logger = AuditLogger()
    logger.logger.handlers.clear()
    return logger

@pytest.fixture
def masker_with_audit(audit_logger):
    from maskinfly.masker import Masker
    return Masker(audit_enabled=True, audit_logger=audit_logger)

@pytest.fixture
def masker_no_audit():
    from maskinfly.masker import Masker
    return Masker(audit_enabled=False)

# Фикстура для пропуска асинхронных тестов, если pytest-asyncio не установлен
def pytest_runtest_setup(item):
    if 'asyncio' in item.keywords and not HAS_ASYNCIO:
        pytest.skip("pytest-asyncio not installed, skipping async test")
