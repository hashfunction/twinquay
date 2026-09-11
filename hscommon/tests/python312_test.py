from hscommon import pygettext


def test_translation_source_discovery(tmp_path):
    package = tmp_path / "translation_sample"
    package.mkdir()
    (package / "__init__.py").write_text("")
    source = package / "sample.py"
    source.write_text("")
    assert pygettext._get_modpkg_path("translation_sample.sample", [str(tmp_path)]) == str(source)
    assert str(source) in pygettext.getFilesForName(str(package))
