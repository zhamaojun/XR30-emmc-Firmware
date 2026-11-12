"""Offline checks for scripts/verify_images.py (no build, no router)."""
import importlib.util
import io
import pathlib
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_verify():
    spec = importlib.util.spec_from_file_location(
        "xr30_verify_images", ROOT / "scripts/verify_images.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_image(path, kernel_size, root_size, folder="sysupgrade-cmcc_rax3000m-emmc"):
    with tarfile.open(path, "w") as tar:
        for name, size in (("kernel", kernel_size), ("root", root_size)):
            info = tarfile.TarInfo(f"{folder}/{name}")
            info.size = size
            tar.addfile(info, io.BytesIO(b"\0" * size))


class VerifyImagesTests(unittest.TestCase):
    def test_tar_sizes_reads_kernel_and_root(self):
        v = load_verify()
        with tempfile.TemporaryDirectory() as temp:
            image = pathlib.Path(temp) / "openwrt-sysupgrade.bin"
            write_image(image, 1024, 2048)
            self.assertEqual(v.tar_sizes(image), (1024, 2048))

    def test_limit_errors_flags_oversized_parts(self):
        v = load_verify()
        self.assertEqual(v.limit_errors(1, 1), [])
        self.assertTrue(v.limit_errors(v.KERNEL_LIMIT + 1, 1))
        self.assertTrue(v.limit_errors(1, v.ROOT_LIMIT + 1))

    def test_main_fails_on_oversized_kernel(self):
        v = load_verify()
        with tempfile.TemporaryDirectory() as temp:
            temp_path = pathlib.Path(temp)
            write_image(temp_path / "x-sysupgrade.bin", v.KERNEL_LIMIT + 1, 4096)
            old_cwd, old_argv = pathlib.Path.cwd(), sys.argv
            try:
                import os
                os.chdir(temp_path)
                sys.argv = ["verify_images.py", str(temp_path)]
                self.assertEqual(v.main(), 1)
                self.assertIn("FAIL", (temp_path / "image-inventory.txt").read_text())
            finally:
                os.chdir(old_cwd)
                sys.argv = old_argv

    def test_main_passes_fitting_image(self):
        v = load_verify()
        with tempfile.TemporaryDirectory() as temp:
            temp_path = pathlib.Path(temp)
            write_image(temp_path / "x-sysupgrade.bin", 1024, 2048)
            old_cwd, old_argv = pathlib.Path.cwd(), sys.argv
            try:
                import os
                os.chdir(temp_path)
                sys.argv = ["verify_images.py", str(temp_path)]
                self.assertEqual(v.main(), 0)
            finally:
                os.chdir(old_cwd)
                sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
