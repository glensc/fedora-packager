import os
import sys
import unittest
import shutil
import tempfile

from spec import Spec

class TestSpec(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._basedir = os.path.dirname(sys.modules['__main__'].__file__)
        self._clutter_specpath = os.path.join(self._basedir, 'clutter.spec')

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def testBuildSectionFilter(self):
        spec = Spec(self._clutter_specpath)
        def build_filter(line):
            if line.startswith('%configure'):
                return 'autogen.sh && ' + line
            return None
        spec.add_section_filter('%build', build_filter)
        new_specpath = os.path.join(self._tmpdir, os.path.basename(self._clutter_specpath))
        spec.save_as(new_specpath)
        f = open(new_specpath)
        found_autogen = False
        for line in f:
            if line.startswith('autogen.sh && %configure'):
                found_autogen = True
                break
        f.close()
        self.assertTrue(found_autogen)

    def testIncrementRelease(self):
        spec = Spec(self._clutter_specpath)
        spec.increment_release_snapshot('git1a0b2c')
        new_specpath = os.path.join(self._tmpdir, os.path.basename(self._clutter_specpath))
        spec.save_as(new_specpath)
        spec2 = Spec(new_specpath)
        release = spec2.get_key('Release')
        self.assertEquals(release, '4.0.git1a0b2c%{?dist}')

if __name__ == '__main__':
    unittest.main()
