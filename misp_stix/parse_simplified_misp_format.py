#!/usr/bin/env python3
import json
import operator
import sys
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from pymisp import MISPEvent


class MispParser():
    def __init__(self, original, modified):
        self.original = original
        self.modified = modified
        self.recovering = {'original': {}, 'modified': {}}

    @staticmethod
    def _create_debug_message(feature='slight changes'):
        message = f'Some {feature} appeared during the export/import process'
        if len(message) % 2 != 0:
            message = f'{message}.'
        spaces = int((78 - len(message)) / 2)
        print(f"{'#' * 80}\n#{' ' * spaces}{message.upper()}{' ' * spaces}#\n{'#' * 80}\n")

    @staticmethod
    def _debug_changes(original, modified):
        original_name = tuple(original.keys())[0]
        modified_name = tuple(modified.keys())[0]
        original_values = original[original_name]
        modified_values = modified[modified_name]
        original_type = 'object' if isinstance(original_values, dict) else 'attribute'
        modified_type = 'object' if isinstance(modified_values, dict) else 'attribute'
        print(f'The {original_type} {original_name}:')
        print(f'{json.dumps(original_values, indent=4) if original_type == "object" else original_values}')
        if original_type != modified_type:
            print(f'Became an {modified_type} {modified_name}:')
        else:
            print('Has changed and became:')
        print(f'{json.dumps(modified_values, indent=4) if modified_type == "object" else modified_values}\n{"-" * 80}\n')

    @staticmethod
    def _debug_single_feature(feature):
        object_name = tuple(feature.keys())[0]
        values = feature[object_name]
        object_type = 'object' if isinstance(values, dict) else 'attribute'
        print(f'The {object_type} {object_name}:')
        print(json.dumps(values, indent=4) if object_type == 'object' else values)

    def _fetch_modified_from_issues(self, original, modified):
        original_name = tuple(original.keys())[0]
        original_values = original[original_name]
        for mod_id, mod_values in modified.items():
            modified_name = tuple(mod_values.keys())[0]
            if original_name != modified_name:
                continue
            if self._is_included(original_values, mod_values[modified_name]):
                return modified.pop(mod_id)
        return None

    @staticmethod
    def _get_datetime_value(value):
        return datetime.strftime(value, '%Y-%m-%d %H:%M:%S')

    @staticmethod
    def _get_galaxy(galaxy_list):
        galaxies = set()
        for galaxy in galaxy_list:
            galaxies.update({cluster['tag_name'] for cluster in galaxy['GalaxyCluster']})
        return galaxies

    @staticmethod
    def _get_tags(tags):
        return sorted({tag.name for tag in tags if tag.name not in ('Threat-Report', 'misp:tool=\"misp2stix2\"')})

    @staticmethod
    def _get_value(value):
        return value[0] if isinstance(value, list) and len(value) == 1 else value

    def _is_included(self, original, modified):
        if isinstance(original, dict):
            if isinstance(modified, dict):
                if all(value in modified.values() for value in original.values()):
                    return True
                if all(value in original.values() for value in modified.values()):
                    return True
                return False
            return any(modified in value for value in original.values())
        if isinstance(modified, dict):
            return any(original in value for value in modified.values())
        return any((modified in original, original in modified))

    def _jsonify(self, data):
        return {key: self._jsonify(value) if isinstance(value, dict) else self._get_value(value) for key, value in sorted(data.items(), key=operator.itemgetter(0))}

    def _parse_event(self, feature):
        misp_event = MISPEvent()
        misp_event.load_file(getattr(self, feature))
        attributes = defaultdict(dict)
        object_attributes = defaultdict(dict)
        tags = defaultdict(set)
        for attribute in misp_event.attributes:
            attributes[attribute.type][attribute.uuid] = attribute.value
            self.recovering[feature][attribute.uuid] = {attribute.type: attribute.value}
            if attribute.tags:
                tags[attribute.uuid].update(self._get_tags(attribute.tags))
            if 'Galaxy' in attribute and attribute['Galaxy']:
                tags[attribute.uuid].update(self._get_galaxy(attribute['Galaxy']))
        for misp_object in misp_event.objects:
            object_dict = defaultdict(list)
            for attribute in misp_object.attributes:
                object_dict[attribute.object_relation].append(self._get_datetime_value(attribute.value) if attribute.type == 'datetime' else attribute.value)
            simplified_attributes = self._jsonify(object_dict)
            self.recovering[feature][misp_object.uuid] = {misp_object.name: simplified_attributes}
            references = [{'target': reference.referenced_uuid, 'relationship': reference.relationship_type} for reference in misp_object.references]
            object_attributes[misp_object.name][misp_object.uuid] = {'Attribute': simplified_attributes, 'ObjectReference': references}
        if misp_event.tags:
            tags[misp_event.uuid].update(self._get_tags(misp_event.tags))
        if 'Galaxy' in misp_event and misp_event['Galaxy']:
            tags[misp_event.uuid].update(self._get_galaxy(misp_event['Galaxy']))
        tags = {key: list(values) for key, values in tags.items()}
        event = {'Attribute': self._jsonify(attributes),
                 'Object': self._jsonify(object_attributes),
                 'Tag&Galaxy': self._jsonify(tags)}
        filename = f'{misp_event.uuid}_{feature}.json'
        with open(filename, 'wt', encoding='utf-8') as f:
            f.write(json.dumps(event, indent=4))
        print(f'{filename} generated')
        return filename

    def parse_misp_events(self):
        filename = 'MISPEvents2simplified.json'
        matching = {getattr(self, feature): self._parse_event(feature) for feature in ('original', 'modified')}
        print()
        try:
            with open(filename, 'rt', encoding='utf-8') as f:
                mapping = json.loads(f.read())
            mapping.update(matching)
            with open(filename, 'wt', encoding='utf-8') as f:
                f.write(json.dumps(mapping, indent=4))
        except FileNotFoundError:
            with open(filename, 'wt', encoding='utf-8') as f:
                f.write(json.dumps(matching, indent=4))
        self._recover_uuids_issues()

    def _recover_uuids_issues(self):
        issues = {'modified': {}, 'original': {}}
        changes = {'modified': {}, 'original': {}}
        features = ('original', 'modified')
        for original, modified in zip(features, features[::-1]):
            for id, values in self.recovering[original].items():
                if id not in self.recovering[modified]:
                    issues[original][id] = values
                    continue
                if values != self.recovering[modified][id]:
                    changes[original][id] = values
        if changes['original']:
            self._create_debug_message()
            for id, values in changes['original'].items():
                modified = changes['modified'][id]
                self._debug_changes(values, modified)
        if issues['original'] or issues['modified']:
            mapping = {}
            for id, values in issues['original'].items():
                modified = self._fetch_modified_from_issues(values, issues['modified'])
                if not modified:
                    continue
                mapping[id] = modified
            for id, modified in mapping.items():
                original = issues['original'].pop(id)
                if original == modified:
                    self._debug_single_feature(original)
                    print(f'Got another uuid during the export/import process.\n{"-" * 80}\n')
                else:
                    self._debug_changes(original, modified)
            if issues['original'] or issues['modified']:
                self._create_debug_message(feature='issues')
                for original in issues['original'].values():
                    self._debug_single_feature(original)
                    print(f'Got lost during the export/import process.\n{"-" * 80}\n')
                for modified in issues['modified'].values():
                    self._debug_single_feature(modified)
                    print(f'Has been imported from a stix object that was not supposed to be imported this way.\n{"-" * 80}\n')


if __name__ == '__main__':
    parser = ArgumentParser(description='Get simplified attributes with their type (for single attributes) or object relation (for objects attributes) and value.')
    parser.add_argument('-o', '--original', required=True, help='Name of the original MISP event file, in json format, before it is exported in STIX format.')
    parser.add_argument('-m', '--modified', required=True, help='Name of the MISP event file generated with the stix to misp import script.')
    args = parser.parse_args()
    parser = MispParser(args.original, args.modified)
    parser.parse_misp_events()
