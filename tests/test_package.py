def test_package_exposes_version() -> None:
    import wikix

    assert wikix.__version__ == "0.1.0"
