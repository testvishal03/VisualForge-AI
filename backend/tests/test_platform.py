import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.llm.gguf_llm import gpu_layers, runtime_env
from backend.services import media_tools


class MediaToolsTests(unittest.TestCase):
    def setUp(self):
        media_tools.compositor_dir.cache_clear()

    def tearDown(self):
        media_tools.compositor_dir.cache_clear()

    def test_the_compositor_for_this_platform_is_chosen_with_the_right_file_names(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('compositor-win32-x64-msvc', 'compositor-linux-x64-gnu'):
                (root / 'renderer/node_modules/@remotion' / name).mkdir(parents=True)
            with patch.object(sys, 'platform', 'linux'), patch('platform.machine', return_value='x86_64'):
                self.assertEqual(media_tools.ffmpeg(root), root / 'renderer/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg')
            media_tools.compositor_dir.cache_clear()
            with patch.object(sys, 'platform', 'win32'), patch('platform.machine', return_value='AMD64'):
                self.assertEqual(media_tools.ffprobe(root), root / 'renderer/node_modules/@remotion/compositor-win32-x64-msvc/ffprobe.exe')

    def test_a_missing_compositor_says_how_to_fix_it(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'renderer/node_modules/@remotion').mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, 'npm install'):
                media_tools.compositor_dir(Path(d))


class GpuSettingTests(unittest.TestCase):
    def test_the_language_model_stays_on_the_cpu_unless_asked(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('VISUALFORGE_GPU_LAYERS', None)
            self.assertEqual(gpu_layers(), 0)
        with patch.dict(os.environ, {'VISUALFORGE_GPU_LAYERS': '99'}):
            self.assertEqual(gpu_layers(), 99)
        with patch.dict(os.environ, {'VISUALFORGE_GPU_LAYERS': 'all'}), self.assertRaises(ValueError):
            gpu_layers()

    @unittest.skipIf(os.name == 'nt', 'library paths apply to Linux servers')
    def test_linux_servers_find_their_bundled_libraries(self):
        self.assertTrue(runtime_env('/opt/llama/llama-server')['LD_LIBRARY_PATH'].startswith('/opt/llama:'))


if __name__ == '__main__':
    unittest.main()
