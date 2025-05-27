import pytest
from django.contrib.auth.models import User
from django.conf import settings
from pathlib import Path
import tempfile
import shutil

@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }

@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(username='testuser', password='password123')
    return user

@pytest.fixture
def authenticated_client(client, test_user):
    """Django test client with a logged-in test user."""
    client.login(username='testuser', password='password123')
    return client

@pytest.fixture(scope='session')
def test_data_path():
    """Path to the test_data directory."""
    return Path(__file__).parent.parent / "test_data"

@pytest.fixture(scope='function')
def temp_media_root():
    """Create a temporary directory for MEDIA_ROOT and user history for tests."""
    with tempfile.TemporaryDirectory() as tmpdir_base:
        
        # Temporary directory for where 'his_pic' would be based
        # This allows views.py to create user/date subdirs without affecting project
        temp_his_pic_base = Path(tmpdir_base) / "his_pic_test_base"
        temp_his_pic_base.mkdir(parents=True, exist_ok=True)

        # Temporary directory specifically for what would be user_converted_dir / user_upload_dir
        # This is a bit redundant if views.py reconstructs the full path from a base,
        # but useful if we want a predictable 'output' like dir for inspection.
        # For now, let's assume views.py will build its full path from a base.
        # We will override settings.BASE_DIR for the 'his_pic' calculation,
        # or a more specific setting if available.
        # Let's simulate settings.BASE_DIR pointing to temp_his_pic_base's parent for 'his_pic' path construction.
        # views.py uses: os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, today_date_str)
        # So we need a 'settings.BASE_DIR' that, when 'his_pic' is appended, points into our temp structure.

        # Let's use a simpler approach: override a custom setting if the app uses one,
        # or ensure that settings.MEDIA_ROOT is used in a way that can be controlled.
        # The current views.py uses settings.BASE_DIR directly for 'his_pic'.
        # We will override settings.BASE_DIR for the scope of tests needing file generation.
        # This is a bit heavy-handed. A better long-term solution would be a dedicated
        # setting in the app for the root of 'his_pic' or using Django's file storage system.

        # For now, let's create a general temp output dir that tests can use if they
        # manually move files or if we can direct output there.
        # The `test_output` dir from requirements.
        actual_test_output_dir = Path(__file__).parent.parent / "test_output"
        actual_test_output_dir.mkdir(exist_ok=True)
        
        # Create a unique subdir within test_output for this test function's run
        # to avoid conflicts if tests run in parallel or leave files behind.
        run_specific_output_dir = actual_test_output_dir / tempfile.mkdtemp(prefix="run_", dir=actual_test_output_dir)
        
        # Store the path to the temporary 'his_pic' base for use in tests
        # This allows tests to construct expected paths within the temp structure.
        # This isn't directly overriding settings.BASE_DIR globally here, but provides a root.
        # Tests will need to use @override_settings for BASE_DIR if they rely on the view's
        # exact path construction: os.path.join(settings.BASE_DIR, 'his_pic', ...)

        # We will return a dictionary of relevant temp paths.
        paths = {
            "HIS_PIC_TEMP_BASE": temp_his_pic_base, # Where user/date specific dirs will be created by the view
            "TEST_SPECIFIC_OUTPUT": run_specific_output_dir # A place in actual test_output for this run
        }

        yield paths

        # Cleanup: shutil.rmtree on run_specific_output_dir is handled by TemporaryDirectory for tmpdir_base.
        # If run_specific_output_dir was outside tmpdir_base, we'd need to clean it.
        # Since run_specific_output_dir is now created *within* the persistent test_output,
        # we should clean it up.
        if run_specific_output_dir.exists():
            shutil.rmtree(run_specific_output_dir)

# Example of how to use override_settings with the temp_media_root fixture in a test:
# from django.test import override_settings
#
# @override_settings(BASE_DIR=temp_media_root_fixture_value["HIS_PIC_TEMP_BASE"].parent)
# def test_my_view_that_writes_files(authenticated_client, temp_media_root_fixture_value):
#     # ... your test logic ...
#     # The view will now use temp_media_root_fixture_value["HIS_PIC_TEMP_BASE"] as the 'his_pic' directory.
#     pass 