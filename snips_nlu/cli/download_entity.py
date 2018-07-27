from __future__ import print_function, unicode_literals

import json
import sys

import plac

from snips_nlu import __about__
from snips_nlu.cli import link
from snips_nlu.cli.utils import (
    PrettyPrintLevel, check_resources_alias, get_compatibility, get_json,
    get_resources_version, install_remote_package, pretty_print)
from snips_nlu.constants import DATA_PATH
# inspired from
# https://github.com/explosion/spaCy/blob/master/spacy/cli/download.py
from snips_nlu.utils import get_package_path


@plac.annotations(
    entity_name=("Name of the builtin entity to download, e.g. "
                 "snips/musicArtist", "positional", None, str),
    direct=("force direct download. Needs entity name with version and "
            "won't perform compatibility check", "flag", "d", bool),
    pip_args=("Additional arguments to be passed to `pip install` when "
              "installing the builtin entity package"))
def download_builtin_entity(resource_name, direct=False, *pip_args):
    """Download compatible language or gazetteer entity resources"""
    if direct:
        url_tail = '{r}/{r}.tar.gz#egg={r}'.format(r=resource_name)
        download_url = __about__.__entities_download_url__ + '/' + url_tail
        exit_code = install_remote_package(download_url, pip_args)
        if exit_code != 0:
            sys.exit(exit_code)
    else:
        shortcuts = get_json(__about__.__shortcuts__, "Resource shortcuts")
        check_resources_alias(resource_name, shortcuts)

        compatibility = get_compatibility()
        resource_name_lower = resource_name.lower()
        long_resource_name = shortcuts.get(resource_name_lower,
                                           resource_name_lower)

        installed_languages = _get_installed_languages()
        if not installed_languages:
            pretty_print(
                "You must download some language resources before you can "
                "install gazetteer entities.",
                "Please run 'python -m snips_nlu download <language>' "
                "with the appropriate language.",
                "Then run 'python -m snips_nlu download %s'" % resource_name,
                title="No language resources installed yet",
                level=PrettyPrintLevel.WARNING, exits=0)

        for language in installed_languages:
            _download_and_link_entity(
                long_resource_name, resource_name, language, compatibility,
                pip_args)


def _download_and_link_entity(long_resource_name, resource_alias, language,
                              compatibility, pip_args):
    full_resource_name = long_resource_name + "_" + language
    version = get_resources_version(full_resource_name, resource_alias,
                                    compatibility)
    entity_name = long_resource_name[10:]  # snips_nlu_xxx
    entity_url = _get_entity_url(language, entity_name, version)
    latest = get_json(entity_url + "/latest",
                      "Latest entity resources version")
    exit_code = install_remote_package(latest["url"], pip_args)
    if exit_code != 0:
        sys.exit(exit_code)
    try:
        # Get package path here because link uses
        # pip.get_installed_distributions() to check if the resource is a
        # package, which fails if the resource was just installed via
        # subprocess
        package_path = get_package_path(full_resource_name)
        link_alias = entity_name + "_" + language
        link(full_resource_name, link_alias, force=True,
             resources_path=package_path)
    except:  # pylint:disable=bare-except
        pretty_print(
            "Creating a shortcut link for '%s' didn't work." % resource_alias,
            title="The builtin entity resources were successfully downloaded, "
                  "however linking failed.",
            level=PrettyPrintLevel.WARNING)


def _get_entity_url(language, entity, version):
    if not version.startswith("v"):
        version = "v" + version
    return "/".join(
        [__about__.__entities_download_url__, language, entity, version])


def _get_installed_languages():
    languages = set()
    for directory in DATA_PATH.iterdir():
        metadata_file = directory / "metadata.json"
        if not directory.is_dir() or not metadata_file.exists():
            continue
        with metadata_file.open(encoding="utf8") as f:
            metadata = json.load(f)
        languages.add(metadata["language"])
    return languages


def _get_installed_entities():
    languages = set()
    for directory in DATA_PATH.iterdir():
        if not directory.is_dir():
            continue
        with (directory / "metadata.json").open(encoding="utf8") as f:
            metadata = json.load(f)
        languages.add(metadata["language"])
    return languages
