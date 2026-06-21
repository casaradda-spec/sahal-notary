import shutil
import tempfile

from django.test import TestCase, override_settings


class TempMediaTestCase(TestCase):
    """TestCase that redirects MEDIA_ROOT to a throwaway temp dir for the
    duration of the test class, so signature/seal image uploads in tests
    don't pollute the real media/ directory."""

    @classmethod
    def setUpClass(cls):
        cls._temp_media_dir = tempfile.mkdtemp(prefix='sahal_test_media_')
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media_dir, ignore_errors=True)
