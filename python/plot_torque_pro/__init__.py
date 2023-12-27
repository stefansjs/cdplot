"""
Package for plot_torque_pro
"""


def get_version():
    """ Returns the package and build version of plot_torque_pro """
    from pathlib import Path
    package_directory = Path(__file__).parent
    version_file = package_directory / 'VERSION'

    if version_file.exists():
        import toml
        version_info = toml.load(version_file)
        return version_info['__version__']

    from datetime import date
    return f'UNKNOWN+{date.today().strftime("%Y.%m.%d")}'


__version__ = get_version()
